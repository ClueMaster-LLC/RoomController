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

log_level = 1    #0 for disabled | 1 for details

#device hardware
cm_dc16_banks = 2
cm_dc16_inputs = 8
cm_dc32_banks = 4
cm_dc32_inputs = 32
cm_dc48_banks = 6
cm_dc48_inputs = 48

device_model = 'cm_dc16'  # set by API when scanning or from config file if connected prior

bank_total = (cm_dc16_banks)-1
input_total = (cm_dc16_inputs)

class ConnectAndStream(threading.Thread):
    def __init__(self, ip_address):
        super(ConnectAndStream, self).__init__()
        # the ConnectAndStream thread is started after the ip address is saved in a file
        # global attributes
        self.active = None
        self.ip_address = ip_address

    def run(self):
        connected = False
        while not connected:
            try:
                print('>>> Console Output - Connecting to ' + str(self.ip_address))
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(1.0)
                client_socket.connect((self.ip_address, SERVER_PORT))
                print('>>> Console Output - Connected to ' + str(self.ip_address))
                connected = True
            except socket.error:
                print('The last known IP ' + str(self.ip_address) + ' is no longer valid. Searching for device... '
                                                                    'NOTE****  THIS ONLY WORKS WITH THE REAL NCD '
                                                                    'NETWORK CARDS AND NOT THE SIMULATOR. TO CONNECT '
                                                                    'TO THE SIMULATOR YOU MUST SET THE IP ADDRESS IN '
                                                                    'THE lastKnownIP.json FILE IN THE APPDATA FOLDER.')

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

                    data_responce = (ncd.get_dc_bank_status(0,bank_total))
                    data_responce_new = (data_responce)

                    if data_responce_old != data_responce_new:
                        data_responce_old = data_responce_new

                        # insert SignalR stream
                        print('>>> Console Output - SEND VALUES TO CLUEMASTER API ' + str(data_responce))                        

                        if log_level == 1:
                            print('>>> Console Output - HEX BYTE VALUES RETURNED FROM DEVICE ' + str(bytes(data_responce)))
                            print('>>> Console Output - LIST VALUES RETURNED FROM DEVICE ' + str(data_responce))

                            # make a new array by ignoring the first two bytes and the last byte
                            readings = bytes(data_responce)
                            counter = 0
                            bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                            print('>>> Console Output - Binary values : ', bytes_as_bits)

                            # This code block is only for displaying the of/off of the inputs to the log for diagnostics                            
                            for bank in readings:
                                # increment through each input
                                for i in range(0, input_total):
                                    # << indicates a bit shift. Basically check corresponding bit in the reading
                                    state = (bank & (1 << i))
                                    if state != 0:
                                        # print('Input '+ str(bank) +' is high')
                                        print('>>> Console Output - BANK Unknown: Input ' + str(i + 1) + ' is high' )
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
        localIP = self.extract_ip()
        localPort = 13000
        bufferSize = 1024

        msgFromServer = "Connected"
        bytesToSend = str.encode(msgFromServer)

        # Create a datagram socket
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Bind to address and ip
        UDPServerSocket.bind((localIP, localPort))

        print("UDP server up - Discovering Devices")

        # Listen for incoming datagrams
        while True:
            bytes_address_pair = UDPServerSocket.recvfrom(bufferSize)

            message = bytes_address_pair[0]
            address = bytes_address_pair[1]
            client_ip = ((bytes_address_pair[1])[0])

            #client_msg = "Message from Device:{}".format(message)
            discover_ip = "Device found - IP Address:{}".format(address)

            # print(clientMsg)
            print(">>> Console Output - Discovered IP: ", client_ip)
            break

        return client_ip

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
            print(">>> Console Output - Room Controller IP Address - ", ip_address)
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

    def save_device_info(self):
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "device_info.json")
        device_info_dict = {"IP": "", "MacAddress": "", "DeviceType": ""}

        with open(device_info_file, "w") as device_info:
            json.dump(device_info_dict, device_info)


def start_thread():
    if __name__ == "__main__":
        connect_and_stream_instance = ConnectAndStream(ip_address="192.168.1.10")  # enter hardcoded ip
        connect_and_stream_instance.start()


start_thread()
