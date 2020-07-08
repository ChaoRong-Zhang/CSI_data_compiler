class CSI:
    """
    This is a class to hold information from the kernel about the CSI information of the received network packet.
    Attributes:
        buf_len     (int):  length of the buffer in bytes.
        tsf_stamp   (int): time (TSF) of when the packet arrived in microseconds.
        csi_len     (int): length of the portion of the buffer in bytes.
        channel     (int): center frequency of the wireless channel in MHz.
        payload_len (int): length of the payload in the received packet in bytes.
        phyerr      (int): phy error code, 0 if packet received successfully.
        noise       (int): noise floor expressed in dB.
        rate        (int): data rate of the received packet
        chan_bw     (int): channel bandwidth =0 if 20MHz and =1 if 40MHz.
        num_tones   (int): number of sub-carriers that was used in transmission.
        nr          (int): number of receiving antennae
        nc          (int): number of transmitting antennae
        rssi        (int): rssi of combination of all the active chains.
        rssi_0      (int): rssi of active chain 0
        rssi_1      (int): rssi of active chain 1
        rssi_2      (int): rssi of active chain 2
        data        (list of numpy arrays): csi data of the received packet, each array has num_tone complex pairs
    """

    def __init__(self):
        """
        The constructor for the CSI class
        Set each individual thing, avoided having lengthy constructor call
        """
        self.buf_len = 0
        self.tfs_stamp = 0
        self.csi_len = 0
        self.channel = 0
        self.payload_len = 0
        self.phyerr = 0
        self.noise = 0
        self.rate = 0
        self.chan_bw = 0
        self.num_tones = 0
        self.nr = 0
        self.nc = 0
        self.rssi = 0
        self.rssi_0 = 0
        self.rssi_1 = 0
        self.rssi_2 = 0
        self.data = []

    def print_status(self):
        """
        Prints to the terminal the meta data for the received packet
        :return:
        """
        print("Status Report")
        print("csi_len is:      ", self.csi_len)
        print("Channel is:      ", self.channel)
        print("err_info is:     ", self.phyerr)
        print("noise_floor is:  ", self.noise)
        print("Rate is:         ", self.rate)
        print("bandWidth is:    ", self.chan_bw)
        print("num_tones is:    ", self.num_tones)
        print("nr is:           ", self.nr)
        print("nc is:           ", self.nc)
        print("rssi is:         ", self.rssi)
        print("rssi1 is:        ", self.rssi_0)
        print("rssi2 is:        ", self.rssi_1)
        print("rssi3 is:        ", self.rssi_2)
        print("payload_len is:  ", self.payload_len)
        print("")