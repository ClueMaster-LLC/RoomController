import json
import threading
import socket
import time
import os
import sys
import ncd_industrial_devices

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# GLOBAL VARIABLES
SERVER_PORT = 2101
READ_SPEED = 0.05

log_level = 1  # 0 for disabled | 1 for details

# device hardware
cm_dc16_banks = 2
cm_dc16_inputs = 8
cm_dc32_banks = 4
cm_dc32_inputs = 32
cm_dc48_banks = 6
cm_dc48_inputs = 48

# device_model = 'cm_dc16'  # set by API when scanning or from config file if connected prior

bank_total = (cm_dc16_banks) - 1
input_total = (cm_dc16_inputs)


class ConnectAndStream(threading.Thread):
    def __init__(self, device_mac):
        super(ConnectAndStream, self).__init__()
        # the ConnectAndStream thread is started after the ip address is saved in a file
        # global attributes
        self.active = None
        self.device_mac = device_mac
        self.ip_address = (self.read_device_info(self.device_mac)[0])
        self.device_model = (self.read_device_info(self.device_mac)[1])

    def run(self):
        connected = False
        while not connected:
            try:
                print(">>> Console Output - Room Controller IP Address: " + str(self.extract_ip()))
                print('>>> Console Output - Connecting to last known device IP: ' + str(
                    self.ip_address) + '  MAC: ' + str(self.device_mac) + '  Device Model: ' + str(self.device_model))
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(1.0)
                client_socket.connect((self.ip_address, SERVER_PORT))
                print('>>> Console Output - Connected to ' + str(self.ip_address))
                connected = True
            except socket.error:
                print('The last known IP ' + str(
                    self.ip_address) + ' is no longer valid. Searching network for device... ')

                self.ip_address = self.deviceDiscovery()  # find new device IP Address
                print('>>> Console Output - Connecting to ' + str(self.ip_address))
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(1.0)
                client_socket.connect((self.ip_address, SERVER_PORT))
                connected = True

        try:
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            data_responce_old = ''
            print('>>> Console Output - DEVICE CONNECTED AND READY')

            try:
                while 1 == 1:

                    data_responce = (ncd.get_dc_bank_status(0, bank_total))
                    data_responce_new = (data_responce)

                    if data_responce_old != data_responce_new:
                        data_responce_old = data_responce_new

                        # insert SignalR stream
                        print('>>> Console Output - SEND VALUES TO CLUEMASTER SignalR ' + str(data_responce))

                        if log_level == 1:
                            print('>>> Console Output - HEX BYTE VALUES RETURNED FROM DEVICE ' + str(
                                bytes(data_responce)))
                            print('>>> Console Output - LIST VALUES RETURNED FROM DEVICE ' + str(data_responce))

                            # make a new array by ignoring the first two bytes and the last byte
                            readings = bytes(data_responce)
                            counter = 0
                            bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                            print('>>> Console Output - Binary Responce Values : ', bytes_as_bits)

                            # This code block is only for displaying the of/off of the inputs to the log for diagnostics                            
                            for bank in readings:
                                # increment through each input
                                for i in range(0, input_total):
                                    # << indicates a bit shift. Basically check corresponding bit in the reading
                                    state = (bank & (1 << i))
                                    if state != 0:
                                        # print('Input '+ str(bank) +' is high')
                                        print('>>> Console Output - BANK Unknown: Input ' + str(i + 1) + ' is high')
                                    else:
                                        print('>>> Console Output - BANK Unknown: Input ' + str(i + 1) + ' is low')
                                    counter += 1

                    # wait for a few defined seconds
                    time.sleep(READ_SPEED)

            except KeyboardInterrupt:
                print('>>> Console Output - Keyboard Interrupted')
                try:
                    print(">>> Console Output - Connection closed")
                    client_socket.close()
                    sys.exit(0)
                except SystemExit:
                    pass

            except socket.error:
                # set connection status and recreate socket
                self.connection_lost()
                self.run()

        except socket.error:
            # set connection status and recreate socket
            self.connection_lost()
            self.run()

    def connection_lost(self):
        # set connection status and recreate socket
        connected = False
        connect_retry = 0
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1.0)
        client_socket.close()
        print("connection lost... reconnecting")
        while not connected:
            # attempt to reconnect, otherwise sleep for 5 seconds
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(1.0)
                client_socket.connect((self.ip_address, SERVER_PORT))
                connected = True
                print("re-connection successful")
            except socket.error:
                print('searching...' + str(connect_retry))
                connect_retry += 1
                if connect_retry == 15:
                    print('Connection lost. Starting new search')
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(1.0)
                    client_socket.close()
                    try:
                        self.run()
                    except SystemExit:
                        sys.exit(0)
                    else:
                        self.run()
                    finally:
                        self.run()
                continue

    def deviceDiscovery(self):
        try:
            localIP = self.extract_ip()
            localPort = 13000
            bufferSize = 1024

            msgFromServer = "Connected"
            bytesToSend = str.encode(msgFromServer)

            # Create a datagram socket
            UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

            # Bind to address and ip
            UDPServerSocket.bind((localIP, localPort))

            print("UDP server up - Searching Network for Device: " + str(self.device_mac))

            # Listen for incoming datagrams
            while True:
                try:
                    bytes_address_pair = UDPServerSocket.recvfrom(bufferSize)
                    print(list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))

                    # data returned# ['192.168.1.19', '0008DC21DDFD', '2101', 'NCD.IO', '2.4\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00']

                    discover_ip = ((bytes_address_pair[1])[0])
                    discover_mac = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[1]
                    discover_port = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[2]
                    discovery_mfr = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[3]
                    discovery_version = \
                    (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[4]
                    discover_model = "cm_dc16"

                    print(">>> Console Output - Discovered IP:  ", discover_ip)
                    print(">>> Console Output - Discovered MAC: ", discover_mac)
                    print(">>> Console Output - Discovered Model: ", discover_model)
                    print(">>> Console Output - Discovered Version: ", discovery_version)

                    break
                except socket.error:  ## chagne to exception:
                    print(">>> Console Output - Error trying discovery device")
            self.save_device_info(discover_ip, discover_mac, discover_model)
        except socket.error:  ## chagne to exception:
            print(">>> Console Output - Error trying open UDP discovery port")

        return discover_ip

    @staticmethod
    def extract_ip():
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            st.connect(('10.255.255.255', 1))
            ip_address = st.getsockname()[0]
        except Exception:
            ip_address = '127.0.0.1'
            print(">>> Console Output - Error trying to find Room Controller IP, Defaulting to 127.0.0.1")
        finally:
            st.close()
        return ip_address

    def reboot_device(self):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            ncd.device_reboot()
            client_socket.close()
            print(">>> Console Output - Device Rebooted")
        except Exception:
            print(">>> Console Output - Error Sending Reboot Command")

    def save_device_info(self, ip, i_mac, device_model):
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        device_info_dict = {"Device1": {"IP": ip, "MacAddress": i_mac, "DeviceModel": device_model}}

        with open(device_info_file, "w") as device_info:
            json.dump(device_info_dict, device_info)

    def read_device_info(self, i_mac):
        try:
            device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
            with open(device_info_file, "r") as device_info:
                device_info_response = json.load(device_info)

            for i in device_info_response.items():
                values = i[1]
                if values["MacAddress"] == i_mac:
                    # print("Matched..")
                    return values["IP"], values["DeviceModel"]
                else:
                    # print("Device record does not exist")
                    return ['127.0.0.1', 'not_found']

        except Exception:
            print(">>> Console Output - device_info file does not exist")


def start_thread():
    if __name__ == "__main__":
        # connect_and_stream_instance = ConnectAndStream(ip_address="192.168.1.10")  # enter hardcoded ip
        connect_and_stream_instance = ConnectAndStream(device_mac="0008DC21DDFD")  # enter hardcoded MAC
        connect_and_stream_instance.start()


start_thread()
