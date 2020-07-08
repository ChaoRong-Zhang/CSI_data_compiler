import os
import struct
import sys
import socket
import signal
import time
from datetime import datetime

import numpy as np

from CSI_Class import *


BUFF_SIZE = 4096  # amount of bytes to read from buffer
CSI_ST_LEN = 23  # length of CSI state in buffer (bytes)
BIT_RESOLUTION = 10  # bit resolution for the CSI data
NATIVE_UNSIGNED_LONG_LONG = "=Q"  # Unpacking 8 bytes
NATIVE_UNSIGNED_SHORT = "=H"  # Unpacking 2 bytes
NATIVE_UNSIGNED_CHAR = "=B"  # Unpacking 1 byte

SECONDS_TO_RUN = 30
DB_THRESHOLD = 40.0


PING_PAYLOAD_SIZE = 766
PACKET_SIZE = 1024


def open_csi_device():
    """
    Open and return file buffer to read CSI data from.
    /dev/CSI_dev may need be given read and write permissions
    """
    try:
        fd = os.open("/dev/CSI_dev", os.O_RDWR)
        return fd
    except FileNotFoundError:
        print("Failed to open the device....")


def close_csi_device(fileName):
    """
    Close CSI_dev file (Buffer).
    :param fileName: opened CSI_dev file
    :return:
    """
    os.close(fileName)


def read_csi_data(fd, BUFFSIZE):
    """
    Read CSI status and CSI data from file buffer to our own buffer
    :param fd: opened file buffer
    :param BUFFSIZE: size to read from file buffer
    :return: how many bytes were read from file buffer, our buffer (buffer contains bytes)
    """
    info_array = bytearray(BUFFSIZE)
    cnt = os.readv(fd, [info_array])
    return cnt, info_array


def record_status(buff, cnt):
    """
    Retrieve meta data from buffer about received packet
    :param buff: buffer to read from
    :param cnt: how many bytes are in the buffer
    :return: csi_object full of meta/status data
    """
    two_byte = struct.Struct(NATIVE_UNSIGNED_SHORT)
    meta_struct = struct.Struct("=QHHBBBBBBBBBBBH")

    # csi_object = CSI()
    # csi_object.time_stamp = datetime.now(tz=None).__str__()
    meta_data = meta_struct.unpack(buff[0:25])
    # csi_object.tfs_stamp = meta_data[0]
    # csi_object.csi_len = meta_data[1]
    # csi_object.channel = meta_data[2]
    # csi_object.phyerr = meta_data[3]
    # csi_object.noise = meta_data[4]
    # csi_object.rate = meta_data[5]
    # csi_object.chan_bw = meta_data[6]
    # csi_object.num_tones = meta_data[7]
    # csi_object.nr = meta_data[8]
    # csi_object.nc = meta_data[9]
    # csi_object.rssi = meta_data[10]
    # csi_object.rssi_0 = meta_data[11]
    # csi_object.rssi_1 = meta_data[12]
    # csi_object.rssi_2 = meta_data[13]
    # csi_object.payload_len = meta_data[14]
    buf_len = two_byte.unpack(buff[cnt - 2: cnt])[0]

    # return csi_object
    return meta_data, buf_len


def bit_convert(data, max_bit):
    """
    Checks sign bit of given data based on resolution; if set, convert to negative number.
    :param data: bits to check
    :param max_bit: bit resolution
    :return: check and potentially modified CSI data (real or imaginary)
    """
    sign_bit = data & (1 << (max_bit - 1))
    if sign_bit > 0:
        data -= 1 << max_bit
    return data


def record_CSI_data(buff, nr, nc, num_tones, from_file):
    """
    Read CSI data from buffer
    :param buff: csi data buffer
    :param num_tones: number of sub-carriers
    :param nc: number of transmitting antennae
    :param nr: number of receiving antennae
    :param from_file: reading from a file instead of kernel?
    :return: csi_data divided into different groups
    """

    # list of numpy arrays to hold CSI data
    data = []
    for x in range(0, nr * nc):
        data.append(np.empty(num_tones, dtype=np.complex))

    index = CSI_ST_LEN + 2  # starting index
    if from_file:
        index = 0  # if reading from a file start at the beginning of given buffer

    bits_left = 16
    bit_mask = (1 << BIT_RESOLUTION) - 1  # mask to select BIT_RESOLUTION number of bits

    two_bytes = struct.Struct("=H")

    # grab 2 bytes(16bits) from current spot in buffer
    h_data = two_bytes.unpack(buff[index : index + 2])[0]
    index += 2
    current_data = h_data & ((1 << 16) - 1)

    # loop for each sub-carrier
    for tone_idx in range(0, num_tones):

        # loop for each transmitter antenna
        for nc_idx in range(0, nc):

            # loop for each receiving antenna
            for nr_idx in range(0, nr):

                # Check to see if more bits are needed in current data
                if (bits_left - BIT_RESOLUTION) < 0:
                    # grab 2 bytes(16bits) from current spot in buffer
                    h_data = two_bytes.unpack(buff[index : index + 2])[0]
                    index += 2
                    current_data += h_data << bits_left
                    bits_left += 16

                # grab lowest 10 bits and process
                imag = current_data & bit_mask
                imag = bit_convert(imag, BIT_RESOLUTION)  # check sign bit

                bits_left -= BIT_RESOLUTION
                current_data >>= BIT_RESOLUTION

                # Check to see if more bits are needed in current data
                if (bits_left - BIT_RESOLUTION) < 0:
                    # grab 2 bytes(16bits) from current spot in buffer
                    h_data = two_bytes.unpack(buff[index : index + 2])[0]
                    index += 2
                    current_data += h_data << bits_left
                    bits_left += 16

                # grab lowest 10 bits and process
                real = current_data & bit_mask
                real = bit_convert(real, BIT_RESOLUTION)

                bits_left -= BIT_RESOLUTION
                current_data >>= BIT_RESOLUTION

                # create complex pair and put in list of numpy arrays
                complex_pair = complex(real, imag)
                data[nc_idx * nr + nr_idx][tone_idx] = complex_pair
    return data


def dB_per_array(npArray):
    return 20 * np.log10(np.abs(npArray))


def process_CSI(CSI_data_list, range_threshold):
    """
    Process the CSI data
    :param CSI_data_list: list of numpy arrays
    :param range_threshold: range in desired units
    :return:
    """
    # csi_data_sets = len(CSI_data_list)
    sets_state = [None] * 2

    # access each individual numpy array
    for data_set in range(2):
        subcarriers_db = dB_per_array(CSI_data_list[data_set])
        set_range = np.amax(subcarriers_db) - np.amin(subcarriers_db)
        sets_state[data_set] = set_range <= range_threshold

    return sets_state  # contains a boolean for each set of subcarriers


def process_CSI_Average_Magnitude(CSI_data_list, average_level):
    # csi_data_len = len(CSI_data_list)
    sets_state = [None] * 2
    for data_set in range(2):
        average = np.mean(np.abs(CSI_data_list[data_set]))
        sets_state[data_set] = average >= average_level
    return sets_state


def process_CSI_Average_dB(CSI_data_list, average_level):
    # csi_data_len = len(CSI_data_list)
    sets_state = [None] * 2
    for data_set in range(2):
        average = np.mean(dB_per_array(CSI_data_list[data_set]))
        sets_state[data_set] = average >= average_level
    return sets_state


def to_file(opened_file, buffer, buf_len):
    """
    Write information to opened_file
    :param opened_file: already opened file
    :param buffer: data to be written
    :param buf_len: length of the buffer
    :param time_stamp: absolute time stamp of received packet
    :return:
    """
    opened_file.write(struct.pack("=H", buf_len))

    opened_file.write(buffer)


def main():
    """
    Main fucntion that loops until signaled to exit
    :return:
    """

    def handler(signal_received, frame):
        """
        Handles shutdown gracefully when SIGINT or CTRL-C is detected
        :param signal_received:
        :param frame:
        :return:
        """
        # Handle any cleanup here
        close_csi_device(fd)
        if log_enabled:
            file_name.close()
        print(" SIGINT or CTRL-C or ALARM detected. Exiting gracefully!")
        print("Packets sent in", SECONDS_TO_RUN, "seconds is: ", packet_count)
        print(
            "Sending byte rate is:",
            packet_count * PACKET_SIZE / SECONDS_TO_RUN,
            "bytes/second",
        )
        exit(0)

    log_enabled = False
    file_name = ""

    if len(sys.argv) == 2:
        try:
            info_file = open("data/info.txt",'r+')
            file_num = int(info_file.read())
            info_file.seek(0)
            info_file.write(str(file_num + 1))
            file_name = open("data/alice" + str(file_num) + ".dat", "wb")
        except IOError:
            print("Couldn't open file: ", sys.argv[1])
            return

        log_enabled = True
        print("Logging enabled, check the data folder for the finished file once program is done")

    if len(sys.argv) > 2:
        print("To many input arguments!")
        return

    # Open CSI device and set CTRL-C interrupt and alarm handler
    fd = open_csi_device()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGALRM, handler)
    message_count = 1

    alice_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pay_file = open("scripture_payload.txt", "rb")
    packet_count = 0
    average_time = 0

    signal.alarm(SECONDS_TO_RUN)

    print("Starting to parse!")

    packet_counter = struct.Struct("=Q")

    while True:

        cnt, buff = read_csi_data(fd, BUFF_SIZE)  # Get buffer from CSI_dev file

        # Wait until bytes were actually read from buffer
        if cnt > 0:
            meta_data, buff_len = record_status(buff, cnt)  # Get meta data of received packet

            # Checks to see if it is most likely the ping from bob
            if meta_data[14] == PING_PAYLOAD_SIZE:
                # data = record_CSI_data(  # Get CSI data of received packet
                #     buff, meta_data[8], meta_data[9], meta_data[7], False
                # )

                packet_count += 1
                alice_sock.sendto(packet_counter.pack(packet_count) + pay_file.read(1024), ("10.10.0.5", 5005))

                if log_enabled:
                    to_file(
                        file_name,
                        buff[0: buff_len],
                        buff_len
                    )


if __name__ == "__main__":
    main()
