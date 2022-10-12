import os
import json
import threading
import time
import sys
import auto_startup
import connected_devices
import socket

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# BASE VARIABLES
SERVER_PORT = 2101
READ_SPEED = 0.05


# RegistrationThread checks for device registration
class RegistrationThread(threading.Thread):
    def __init__(self):
        super(RegistrationThread, self).__init__()
        print(">>> Console Output - RegistrationThread active ....")

        # global attributes
        self.active = None
        self.auto_startup_instance = None

    def run(self):
        self.auto_startup_instance = auto_startup.AutoStartup()
        self.auto_startup_instance.__int__()

        print(">>> Console Output - Stopped Base RegistrationThread ...")
        print(">>> Console Output - Restarting Room Controller ...")
        restart_room_controller()
        return


# ConnectPreviousDevicesThread connect to previously configured devices
class ConnectPreviousDevicesThread(threading.Thread):
    def __init__(self):
        super(ConnectPreviousDevicesThread, self).__init__()
        print(">>> Console Output - ConnectPreviousThread active ....")

        # global attributes
        self.active = None
        self.connected_devices_instance = None

    def run(self):
        self.connected_devices_instance = connected_devices.ConnectedDevices()
        self.connected_devices_instance.__init__()
        print(">>> Console Output - Stopped Base ConnectPreviousDevicesThread ...")
        return


class ConnectAndStream(threading.Thread):
    def __init__(self, ip_address):
        super(ConnectAndStream, self).__init__()
        # the ConnectAndStream thread is started after the ip address is saved in a file

        # global attributes
        self.active = None
        self.ip_address = ip_address

    def run(self):
        connected = False
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while not connected:
            try:
                print('>>> Console Output - Connecting to ' + str(self.ip_address))
                client_socket.connect((self.ip_address, SERVER_PORT))
                print('>>> Console Output - Connected to ' + str(self.ip_address))
                connected = True
            except socket.error:
                print('The last known IP ' + str(self.ip_address) + 'is no longer valid. Searching for device... '
                                                                    'NOTE****  THIS ONLY WORKS WITH THE REAL NCD '
                                                                    'NETWORK CARDS AND NOT THE SIMULATOR. TO CONNECT '
                                                                    'TO THE SIMULATOR YOU MUST SET THE IP ADDRESS IN '
                                                                    'THE lastKnownIP.json FILE IN THE APPDATA FOLDER.')

                client_ip = self.deviceDiscovery()  # find new device IP Address
                print('>>> Console Output - Connecting to ' + str(client_ip))
                client_socket.connect((client_ip, SERVER_PORT))
                connected = True

        try:
            client_socket.sendall(b"\xAA\x04\xFE\xAF\x00\x0F\x6A")  # all ports at once
            rawdata = client_socket.recv(32)
            bank_all = ''  # change to (rawdata[2:-1]) if you don't want init values sent on start
            print('>>> Console Output - Init values sent to API - READY')

            try:
                while 1 == 1:

                    client_socket.sendall(b"\xAA\x04\xFE\xAF\x00\x0F\x6A")  # all ports at once
                    # client_socket.sendall(b"\xAA\x04\xFE\x35\xF3\x04\xD8") #device identification maybe?
                    # client_socket.sendall(b"\xFE\xAF\x00") #sends board Init
                    # client_socket.sendall(b"\xFE\x21")  #tes sends board Init
                    # Board returns this byte string b'\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'

                    rawdata = client_socket.recv(32)
                    bank_all_value = (rawdata[2:-1])

                    if bank_all != bank_all_value:
                        bank_all = bank_all_value

                        print('>>> Console Output - SEND BYTE VALUES TO CLUEMASTER API ' + str(rawdata))
                        print('>>> Console Output - SEND VALUES TO CLUEMASTER API ' + str(rawdata[2]), str(rawdata[3]))

                        # make a new array by ignoring the first two bytes and the last byte
                        readings = (rawdata[2:4])
                        counter = 0
                        bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                        print('>>> Console Output - Binary values : ', bytes_as_bits)

                        for bank in readings:
                            # increment through each input
                            for i in range(0, 8):
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
        # HOST = clientIP  # The server's hostname or IP address
        connected = False
        connect_retry = 0
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.close()
        print("connection lost... reconnecting")
        while not connected:
            # attempt to reconnect, otherwise sleep for 5 seconds
            try:
                client_socket.connect((self.ip_address, SERVER_PORT))
                connected = True
                print("re-connection successful")
                # connectRetry = 0
            except socket.error:
                time.sleep(1)
                print('searching...' + str(connect_retry))
                connect_retry += 1
                if connect_retry == 5:
                    print('Connection lost. Starting new search')
                    client_socket.close()
                    try:
                        self.run()
                    except SystemExit:
                        sys.exit(0)
                    else:
                        os._exit(0)
                    finally:
                        os._exit(0)
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

        print("UDP server up - discovering devices")

        # Listen for incoming datagrams
        while True:
            bytes_address_pair = UDPServerSocket.recvfrom(bufferSize)

            message = bytes_address_pair[0]
            address = bytes_address_pair[1]
            client_ip = ((bytes_address_pair[1])[0])

            client_msg = "Message from Device:{}".format(message)
            discover_ip = "Device found - IP Address:{}".format(address)

            # print(clientMsg)
            print(">>> Console Output - Discovered IP - ", discover_ip)
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
        finally:
            st.close()
            print(">>> Console Output - Device IP Address - ", ip_address)
        return ip_address


# master thread manager
class ThreadManager:
    def __init__(self):
        super(ThreadManager, self).__init__()
        print(">>> Console Output - Starting Thread Manager ....")

        # global attributes
        self.active = None
        self.registration_thread = None
        self.connect_to_previous_device_thread = None
        self.controller_status_thread = None
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.previously_connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        if os.path.isdir(APPLICATION_DATA_DIRECTORY) is False:
            os.makedirs(APPLICATION_DATA_DIRECTORY)
        else:
            pass

        with open(self.roomcontroller_configs_file, "w") as configurations_file:
            input_dictionary = {"connect_previous_device_thread_active": True,
                                "registration_thread_active": True}
            json.dump(input_dictionary, configurations_file)

    def execution_environment(self):
        time.sleep(2)

        if os.path.isfile(self.previously_connected_devices_file):
            self.connect_to_previous_device_thread = ConnectPreviousDevicesThread()
            self.connect_to_previous_device_thread.start()
        else:
            with open(self.roomcontroller_configs_file) as configurations_file:
                configurations_file_data = json.load(configurations_file)

            with open(self.roomcontroller_configs_file, "w") as configurations_file:
                configurations_file_data["connect_previous_device_thread_active"] = False
                json.dump(configurations_file_data, configurations_file)

        # starting registration thread
        self.registration_thread = RegistrationThread()
        self.registration_thread.start()


def restart_room_controller():
    # triggering main function from main.py
    thread_manager = ThreadManager()
