import CSI_Class
import CSI_Python_Parser
import struct
import os
import sys
import numpy as np
import csv


def parse_info(file_name):
    """
    Open the CSI log file and read the data from it into a list of objects
    :param file_name: name of the file to be opened and read
    :return: List of CSI objects
    """

    # try to open the file, if it fails exit the program
    try:
        f = open(file_name, "rb")
    except IOError:
        print("Couldn't open file!")
        sys.exit()

    # get the length of the entire file
    len_of_file = os.stat(file_name).st_size

    csi_packet_info = []
    cur = 0

    one_byte = struct.Struct("=B")
    two_byte = struct.Struct("=H")
    meta_struct = struct.Struct('=QHHBBBBBBBBBBBH')

    while cur < (len_of_file - 4):  # loop until the end of the file is reached

        cur_csi_obj = CSI_Class.CSI()  # Create new CSI obj to fill

        # read all the meta data from the current
        cur_csi_obj.buf_len = two_byte.unpack(f.read(2))[0]

        # time_stamp = f.read(26)
        # cur_csi_obj.time_stamp = time_stamp.decode("utf-8")

        meta_data = meta_struct.unpack(f.read(25))
        cur_csi_obj.tfs_stamp = meta_data[0]
        cur_csi_obj.csi_len = meta_data[1]
        cur_csi_obj.channel = meta_data[2]
        cur_csi_obj.phyerr = meta_data[3]
        cur_csi_obj.noise = meta_data[4]
        cur_csi_obj.rate = meta_data[5]
        cur_csi_obj.chan_bw = meta_data[6]
        cur_csi_obj.num_tones = meta_data[7]
        cur_csi_obj.nr = meta_data[8]
        cur_csi_obj.nc = meta_data[9]
        cur_csi_obj.rssi = meta_data[10]
        cur_csi_obj.rssi_0 = meta_data[11]
        cur_csi_obj.rssi_1 = meta_data[12]
        cur_csi_obj.rssi_2 = meta_data[13]
        cur_csi_obj.payload_len = meta_data[14]

        cur += 53

        # Check to see if there is any CSI data and if so read it from the file
        if cur_csi_obj.csi_len > 0:
            csi_buff = bytearray(f.read(cur_csi_obj.csi_len))
            cur_csi_obj.data = CSI_Python_Parser.record_CSI_data(
                csi_buff, cur_csi_obj.nr, cur_csi_obj.nc, cur_csi_obj.num_tones, True
            )
            cur += cur_csi_obj.csi_len

        # implement payload processing if needed, else just going to skip those bytes
        cur += cur_csi_obj.payload_len
        f.read(cur_csi_obj.payload_len)

        # Create a list of CSI packets
        csi_packet_info.append(cur_csi_obj)

        if cur + 420 > len_of_file:
            break
    return csi_packet_info


def parse_and_data_compile_mag(csi_log_file, num_groupings, bob_csv, eve_csv, output_csv):
    """
    Open the CSI log file and both Bob and Eve csv files and parse them into a data csv file
    :param csi_log_file: log binary file that contains CSI info
    :param num_groupings: number of csi groups to include in output csv file
    :param bob_csv: csv file that contains the sequence numbers that bob collected
    :param eve_csv: csv file that contains the sequence numbers that eve collected
    :param output_csv: output csv that data is written to
    :return: nothing to return but check info in output csv
    """

    # try to open the file, if it fails exit the program
    try:
        f = open(csi_log_file, "rb")
    except IOError:
        print("Couldn't open file!")
        sys.exit()

    # Open output csv and populate the headers
    output = open(output_csv, 'w')
    for x in range(56 * num_groupings):
        output.write(str(int(x / 56)) + '-' + str(x % 56) + ',')
    output.write('Victory\n')

    # get the length of the entire file
    len_of_file = os.stat(csi_log_file).st_size
    bob, eve = process_bob_eve(bob_csv, eve_csv)
    num_packets = 1
    cur = 0

    # Init the binary to ascii objects
    two_byte = struct.Struct("=H")
    meta_struct = struct.Struct('=QHHBBBBBBBBBBBH')

    while cur < (len_of_file - 4):  # loop until the end of the file is reached

        # read all the meta data from the current
        buf_len = two_byte.unpack(f.read(2))[0]

        # Grab the meta from the binary file
        meta_data = meta_struct.unpack(f.read(25))
        # cur_csi_obj.tfs_stamp = meta_data[0]
        # cur_csi_obj.csi_len = meta_data[1]
        # cur_csi_obj.channel = meta_data[2]
        # cur_csi_obj.phyerr = meta_data[3]
        # cur_csi_obj.noise = meta_data[4]
        # cur_csi_obj.rate = meta_data[5]
        # cur_csi_obj.chan_bw = meta_data[6]
        # cur_csi_obj.num_tones = meta_data[7]
        # cur_csi_obj.nr = meta_data[8]
        # cur_csi_obj.nc = meta_data[9]
        # cur_csi_obj.rssi = meta_data[10]
        # cur_csi_obj.rssi_0 = meta_data[11]
        # cur_csi_obj.rssi_1 = meta_data[12]
        # cur_csi_obj.rssi_2 = meta_data[13]
        # cur_csi_obj.payload_len = meta_data[14]

        cur += 53

        # Check to see if there is any CSI data and if so read it from the file and put it on the output csv file
        if meta_data[1] > 0:
            csi_buff = bytearray(f.read(meta_data[1]))
            data = CSI_Python_Parser.record_CSI_data(
                csi_buff, meta_data[8], meta_data[9], meta_data[7], True
            )
            cur += meta_data[1]

            if len(data) == num_groupings:
                victory_score = bobVsEve(bob, eve, num_packets)
                add_data_csv(data, output, num_groupings, victory_score)

            num_packets += 1

        # implement payload processing if needed, else just going to skip those bytes
        cur += meta_data[14]
        f.read(meta_data[14])


        if cur + 420 > len_of_file:
            break
    output.close()
    print("Finished parsing")


def parse_and_data_compile_other(csi_log_file, num_groupings, bob_csv, eve_csv, output_csv):
    """
    Open the CSI log file and both Bob and Eve csv files and parse them into a data csv file
    :param csi_log_file: log binary file that contains CSI info
    :param num_groupings: number of csi groups to include in output csv file
    :param bob_csv: csv file that contains the sequence numbers that bob collected
    :param eve_csv: csv file that contains the sequence numbers that eve collected
    :param output_csv: output csv that data is written to
    :return: nothing to return but check info in output csv
    """

    # try to open the file, if it fails exit the program
    try:
        f = open(csi_log_file, "rb")
    except IOError:
        print("Couldn't open file!")
        sys.exit()

    # Open output csv and populate the headers
    output = open(output_csv, 'w')
    for i in range(num_groupings):
        output.write("Average-" + str(i) + ",")
    for i in range(num_groupings):
        output.write("Variance-" + str(i) + ",")
    for i in range(num_groupings):
        output.write("Max-" + str(i) +",Min-" + str(i) + ",Range-" + str(i) + ",")
    output.write("Victory\n")

    # get the length of the entire file
    len_of_file = os.stat(csi_log_file).st_size
    bob, eve = process_bob_eve(bob_csv, eve_csv)
    num_packets = 1
    cur = 0

    # Init the binary to ascii objects
    two_byte = struct.Struct("=H")
    meta_struct = struct.Struct('=QHHBBBBBBBBBBBH')

    while cur < (len_of_file - 4):  # loop until the end of the file is reached

        # read all the meta data from the current
        buf_len = two_byte.unpack(f.read(2))[0]

        # Grab the meta from the binary file
        meta_data = meta_struct.unpack(f.read(25))
        # cur_csi_obj.tfs_stamp = meta_data[0]
        # cur_csi_obj.csi_len = meta_data[1]
        # cur_csi_obj.channel = meta_data[2]
        # cur_csi_obj.phyerr = meta_data[3]
        # cur_csi_obj.noise = meta_data[4]
        # cur_csi_obj.rate = meta_data[5]
        # cur_csi_obj.chan_bw = meta_data[6]
        # cur_csi_obj.num_tones = meta_data[7]
        # cur_csi_obj.nr = meta_data[8]
        # cur_csi_obj.nc = meta_data[9]
        # cur_csi_obj.rssi = meta_data[10]
        # cur_csi_obj.rssi_0 = meta_data[11]
        # cur_csi_obj.rssi_1 = meta_data[12]
        # cur_csi_obj.rssi_2 = meta_data[13]
        # cur_csi_obj.payload_len = meta_data[14]

        cur += 53

        # Check to see if there is any CSI data and if so read it from the file and put it on the output csv file
        if meta_data[1] > 0:
            csi_buff = bytearray(f.read(meta_data[1]))
            data = CSI_Python_Parser.record_CSI_data(
                csi_buff, meta_data[8], meta_data[9], meta_data[7], True
            )
            cur += meta_data[1]
            if len(data) == num_groupings:
                victory_score = bobVsEve(bob, eve, num_packets)
                add_data_csv_other(data, output, num_groupings, victory_score)

            num_packets += 1

        # implement payload processing if needed, else just going to skip those bytes
        cur += meta_data[14]
        f.read(meta_data[14])


        if cur + 420 > len_of_file:
            break
    output.close()
    print("Finished parsing")


def parse_and_data_compile_other_append(csi_log_file, num_groupings, bob_csv, eve_csv, output_csv):
    """
    Open the CSI log file and both Bob and Eve csv files and parse them into a data csv file
    :param csi_log_file: log binary file that contains CSI info
    :param num_groupings: number of csi groups to include in output csv file
    :param bob_csv: csv file that contains the sequence numbers that bob collected
    :param eve_csv: csv file that contains the sequence numbers that eve collected
    :param output_csv: output csv that data is written to
    :return: nothing to return but check info in output csv
    """

    # try to open the file, if it fails exit the program
    try:
        f = open(csi_log_file, "rb")
    except IOError:
        print("Couldn't open file!")
        sys.exit()

    # Open output csv and populate the headers
    output = open(output_csv, 'a')

    # get the length of the entire file
    len_of_file = os.stat(csi_log_file).st_size
    bob, eve = process_bob_eve(bob_csv, eve_csv)
    num_packets = 1
    cur = 0

    # Init the binary to ascii objects
    two_byte = struct.Struct("=H")
    meta_struct = struct.Struct('=QHHBBBBBBBBBBBH')

    while cur < (len_of_file - 4):  # loop until the end of the file is reached

        # read all the meta data from the current
        buf_len = two_byte.unpack(f.read(2))[0]

        # Grab the meta from the binary file
        meta_data = meta_struct.unpack(f.read(25))
        # cur_csi_obj.tfs_stamp = meta_data[0]
        # cur_csi_obj.csi_len = meta_data[1]
        # cur_csi_obj.channel = meta_data[2]
        # cur_csi_obj.phyerr = meta_data[3]
        # cur_csi_obj.noise = meta_data[4]
        # cur_csi_obj.rate = meta_data[5]
        # cur_csi_obj.chan_bw = meta_data[6]
        # cur_csi_obj.num_tones = meta_data[7]
        # cur_csi_obj.nr = meta_data[8]
        # cur_csi_obj.nc = meta_data[9]
        # cur_csi_obj.rssi = meta_data[10]
        # cur_csi_obj.rssi_0 = meta_data[11]
        # cur_csi_obj.rssi_1 = meta_data[12]
        # cur_csi_obj.rssi_2 = meta_data[13]
        # cur_csi_obj.payload_len = meta_data[14]

        cur += 53

        # Check to see if there is any CSI data and if so read it from the file and put it on the output csv file
        if meta_data[1] > 0:
            csi_buff = bytearray(f.read(meta_data[1]))
            data = CSI_Python_Parser.record_CSI_data(
                csi_buff, meta_data[8], meta_data[9], meta_data[7], True
            )
            cur += meta_data[1]
            if len(data) == num_groupings:
                victory_score = bobVsEve(bob, eve, num_packets)
                add_data_csv_other(data, output, num_groupings, victory_score)

            num_packets += 1

        # implement payload processing if needed, else just going to skip those bytes
        cur += meta_data[14]
        f.read(meta_data[14])


        if cur + 420 > len_of_file:
            break
    output.close()
    print("Finished parsing")


def parse_and_data_compile_append(csi_log_file, num_groupings, bob_csv, eve_csv, output_csv):
    """
    Open the CSI log file and both Bob and Eve csv files and parse them into a data csv file
    :param csi_log_file: log binary file that contains CSI info
    :param num_groupings: number of csi groups to include in output csv file
    :param bob_csv: csv file that contains the sequence numbers that bob collected
    :param eve_csv: csv file that contains the sequence numbers that eve collected
    :param output_csv: output csv that data is written to
    :return: nothing to return but check info in output csv
    """

    # try to open the file, if it fails exit the program
    try:
        f = open(csi_log_file, "rb")
    except IOError:
        print("Couldn't open file!")
        sys.exit()

    # Open output csv and populate the headers
    output = open(output_csv, 'a')

    # get the length of the entire file
    len_of_file = os.stat(csi_log_file).st_size
    bob, eve = process_bob_eve(bob_csv, eve_csv)
    num_packets = 1
    cur = 0

    # Init the binary to ascii objects
    two_byte = struct.Struct("=H")
    meta_struct = struct.Struct('=QHHBBBBBBBBBBBH')

    while cur < (len_of_file - 4):  # loop until the end of the file is reached

        # read all the meta data from the current
        buf_len = two_byte.unpack(f.read(2))[0]

        # Grab the meta from the binary file
        meta_data = meta_struct.unpack(f.read(25))
        # cur_csi_obj.tfs_stamp = meta_data[0]
        # cur_csi_obj.csi_len = meta_data[1]
        # cur_csi_obj.channel = meta_data[2]
        # cur_csi_obj.phyerr = meta_data[3]
        # cur_csi_obj.noise = meta_data[4]
        # cur_csi_obj.rate = meta_data[5]
        # cur_csi_obj.chan_bw = meta_data[6]
        # cur_csi_obj.num_tones = meta_data[7]
        # cur_csi_obj.nr = meta_data[8]
        # cur_csi_obj.nc = meta_data[9]
        # cur_csi_obj.rssi = meta_data[10]
        # cur_csi_obj.rssi_0 = meta_data[11]
        # cur_csi_obj.rssi_1 = meta_data[12]
        # cur_csi_obj.rssi_2 = meta_data[13]
        # cur_csi_obj.payload_len = meta_data[14]

        cur += 53

        # Check to see if there is any CSI data and if so read it from the file and put it on the output csv file
        if meta_data[1] > 0:
            csi_buff = bytearray(f.read(meta_data[1]))
            data = CSI_Python_Parser.record_CSI_data(
                csi_buff, meta_data[8], meta_data[9], meta_data[7], True
            )
            cur += meta_data[1]
            if len(data) == num_groupings:
                victory_score = bobVsEve(bob, eve, num_packets)
                add_data_csv(data, output, num_groupings, victory_score)

            num_packets += 1

        # implement payload processing if needed, else just going to skip those bytes
        cur += meta_data[14]
        f.read(meta_data[14])


        if cur + 420 > len_of_file:
            break
    output.close()
    print("Finished parsing")


def process_bob_eve(bob_csv, eve_csv):
    """
    Create lists of packets received by bob and eve
    :param bob_csv: csv filled with sequence numbers bob received
    :param eve_csv: csv filled with sequence numbers eve received
    """
    bob_csv = open(bob_csv, 'r')
    eve_csv = open(eve_csv, 'r')
    bob_reader = csv.reader(bob_csv, delimiter=",")
    eve_reader = csv.reader(eve_csv, delimiter=",")

    bob_seq = []
    eve_seq = []
    for row in bob_reader:
        bob_seq.append(row[0])
    for row in eve_reader:
        eve_seq.append(row[0])
    return bob_seq, eve_seq


def bobVsEve(bob_array, eve_array, seq_num):
    """
    Determine who is the winner is between bob and eve
    :param bob_array: list of sequence numbers bob collected
    :param eve_array: list of sequence numbers eve collected
    :param seq_num: seq_num to see who won
    """
    bob_value = 0
    eve_value = 0
    if str(seq_num) in bob_array:
        bob_value = 1
    if str(seq_num) in eve_array:
        eve_value = 1
    value = bob_value - eve_value
    if value < 0:
        value = 0
    return value


def add_data_csv(data, csv_file, num_groupings, victory_score):
    """
    add a single line of csi data to a csv
    :param: data: csi groupings
    :param: csv_file: file to add line to
    :param: num_groupings: number of groups of csi to parse
    :param: victory_score: did bob or eve win
    :return:
    """
    for j in range(num_groupings):
        for k in range(56):
            csv_file.write(str(int(round(np.abs(data[j][k])))) + ',')
    csv_file.write(str(victory_score) + '\n')


def add_data_csv_other(data, csv_file, num_groupings, victory_score):
    """
    Add a line of statistical analysis to the output csv
    :param data: List of CSI data
    :param csv_file: output csv file to write to
    :param num_groupings: number of groupings to include
    :param victory_score: who won the packet (bob or eve)
    :return:
    """
    average_list = []
    variance_list = []
    max_list = []
    min_list = []
    for i in range(num_groupings):
        mag = np.abs(data[i])
        average_list.append(np.mean(mag))
        variance_list.append(np.var(mag))
        max_list.append(np.amax(mag))
        min_list.append(np.amin(mag))
    for i in range(num_groupings):
        csv_file.write(str(int(average_list[i])) + ",")
    for i in range(num_groupings):
        csv_file.write(str(int(variance_list[i])) + ",")
    for i in range(num_groupings):
        csv_file.write(str(int(max_list[i])) + "," + str(int(min_list[i])) + "," + str(int(max_list[i]-min_list[i])) + ",")
    csv_file.write(str(victory_score) + '\n')


def create_data_sheet(csi_obj_list, num_groupings, bob_csv, eve_csv, out_file):
    """
    Take a list of csi objects and parse them along with data from bob and eve into a csv
    :param csi_obj_list: list of csi objects
    :param num_groupings: number of groups to record from csi data
    :param bob_csv: csv of sequence numbers from bob
    :param eve_csv: csv of sequence numbers from eve
    :param out_file: csv of data and sequence numbers
    :return:
    """
    bob, eve = process_bob_eve(bob_csv, eve_csv)
    d_tree_file = open(out_file, 'w')

    for x in range(56 * num_groupings):
        d_tree_file.write(str(int(x / 56)) + '-' + str(x % 56) + ',')
    d_tree_file.write('victory\n')
    for i in range(len(csi_obj_list)):
        for j in range(len(csi_obj_list[i].data) if len(csi_obj_list[i].data) < (num_groupings + 1) else num_groupings):
            for k in range(56):
                d_tree_file.write(str(int(round(np.abs(csi_obj_list[i].data[j][k])))) + ',')
        if len(csi_obj_list[i].data) < num_groupings:
            for j in range(num_groupings - len(csi_obj_list[i].data)):
                for k in range(56):
                    d_tree_file.write('0,')
        d_tree_file.write(str(bobVsEve(bob, eve, i + 1)) + '\n')


def main():
    if len(sys.argv) < 7:
        print("python data_compile.py csi_log_file num_groupings bob_csv eve_csv output_csv mode")
        return
    if len(sys.argv) > 7:
        print("To many arguments")
        return
    if sys.argv[6] == '1':
        parse_and_data_compile_mag(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
        print("Done")
    elif sys.argv[6] == '2':
        parse_and_data_compile_other(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
        print("Done")
    elif sys.argv[6] == '3':
        parse_and_data_compile_append(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
        print("Done")
    elif sys.argv[6] == '4':
        parse_and_data_compile_other_append(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
        print("Done")
    else:
        print("Wrong type of mode was provided. Mode 1 is magnitude and Mode 2 is statistical analysis")


if __name__ == "__main__":
    main()
