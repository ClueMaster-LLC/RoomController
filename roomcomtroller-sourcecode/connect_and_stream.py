import json
import threading
import socket
import time
import os
import sys

# GLOBAL VARIABLES
ROOT_DIRECTORY = os.getcwd()
SERVER_PORT = 2101
READ_SPEED = 0.05


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
            
            mem_loc = 144
            send_packet = bytes([254,53,mem_loc])
            while mem_loc < 159:
                client_socket.sendall(send_packet)
                mem_loc = mem_loc+1
                send_packet = bytes([254,53,mem_loc])

                print(str(client_socket.recv(32)))
                
            
            #client_socket.sendall(bytes([254,53,144:159])) #	Contains the Device Name up to 16 Characters.
                                                            #   The device name is useful for indicating a location but may be
                                                            #   used for other applications as well. These 16 bytes may be used
                                                            #   for anything, but we suggest using it for a name so that E3C Device
                                                            #   Discovery can function properly.
                                                            #   Values 144-159 send to query

            bank_all = ''  # change to (rawdata[2:-1]) if you don't want init values sent on start

            print('>>> Console Output - DEVICE CONNECTED AND READY')

            try:
                while 1 == 1:
                    client_socket.sendall(bytes([170,4,254,175,0,15,106]))     # read all ports at once
                    # client_socket.sendall(b"\xAA\x04\xFE\xAF\x00\x0F\x6A")      # send hex read all ports at once
                    # client_socket.sendall(b"\xAA\x04\xFE\x35\xF3\x04\xD8")    #device identification maybe?
                    # client_socket.sendall(b"\xFE\x21\x8C\x63")                #reboots the NCD device #Receive Byte: No Response
                    # client_socket.sendall(bytes([254, 33, 140, 99]))           #reboots the NCD device #Receive Byte: No Response
                    # client_socket.sendall(b"\xFE\xAF\x00")                    #sends board Init    
                    # client_socket.sendall(b"\xFE\x21")                        #tes sends board Init
                    # Board returns this byte string b'\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'

                    rawdata = client_socket.recv(32)
                    bank_all_value = (rawdata[2:-1])

                    if bank_all != bank_all_value:
                        bank_all = bank_all_value

                        print('>>> Console Output - HEX BYTE VALUES RETURNED FROM DEVICE ' + str(rawdata))
                        print('>>> Console Output - LIST VALUES RETURNED FROM DEVICE ' + str(list(rawdata)))
                        print('>>> Console Output - SEND VALUES TO CLUEMASTER API ' + str(list(rawdata[2:4])))

                        # make a new array by ignoring the first two bytes and the last byte
                        banks = 2  #dynamic, pull from device type
                        inputs = 8 #dynamic, pull from device type
                        readings = list(rawdata[2:banks+2])
                        counter = 0
                        bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                        print('>>> Console Output - Binary values : ', bytes_as_bits)

                        for bank in readings:
                            # increment through each input
                            for i in range(0, inputs):
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
            print(">>> Console Output - Room Controller IP Address - ", ip_address)
        return ip_address

def start_thread():
    if __name__ == "__main__":
        connect_and_stream_instance = ConnectAndStream(ip_address="192.168.1.19")  # enter hardcoded ip
        connect_and_stream_instance.start()


start_thread()
