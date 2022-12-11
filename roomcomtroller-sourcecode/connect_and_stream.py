import json
import threading
import socket
import time
import datetime
import os
import platform
import sys
import requests
from apis import *
from requests.structures import CaseInsensitiveDict
import ncd_industrial_devices
import room_controller

## This import will be for signalR code##
import logging
from signalrcore.hub_connection_builder import HubConnectionBuilder
##

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# GLOBAL VARIABLES

log_level = 0  # 0 for disabled | 1 for ALL details | 2 for device input/relay status | 3 for network connections

class ConnectAndStream(threading.Thread):
    def __init__(self, device_mac):
        super(ConnectAndStream, self).__init__()
        # the ConnectAndStream thread is started after the ip address is saved in a file

        # local attributes inside ConnectAndStream
        self.active = None
        print(">>> connect_and_stream - GLOBAL MAC: ", room_controller.global_active_mac_ids)
        self.device_mac = device_mac
        [self.ip_address, self.server_port, self.device_model, self.device_type, self.read_speed, self.input_total, self.relay_total, self.room_id] = self.read_device_info(self.device_mac)
        self.bank_total = ((self.input_total // 8) - 1)
        self.post_input_relay_request_update_api = POST_INPUT_RELAY_REQUEST_UPDATE
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")

        # instance methods
        self.configuration()
        self.signalr_hub()
        print("connect and stream startup completed")
            
    def configuration(self):
        with open(self.unique_ids_file) as unique_ids_file:
            json_response_of_unique_ids_file = json.load(unique_ids_file)

        self.device_unique_id = json_response_of_unique_ids_file["device_id"]
        self.api_bearer_key = json_response_of_unique_ids_file["api_token"]
        self.device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

        self.api_headers = CaseInsensitiveDict()
        self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"
        #print(">>> connect_and_stream - RC Unique ID: " + str(self.device_unique_id))

    def signalr_hub(self):
        self.server_url = "https://devapi.cluemaster.io/chathub"
##        self.token = self.api_bearer_key
##        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.ERROR)
        self.hub_connection = HubConnectionBuilder()\
            .with_url(self.server_url, options={
                "verify_ssl": True,
                "skip_negotiation": False,
                "http_client_options": {"headers": self.api_headers, "timeout": 5.0},
                "ws_client_options": {"headers": self.api_headers, "timeout": 5.0},
                }) \
            .configure_logging(logging.ERROR , socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect({
                    "type": "interval",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    #"max_attempts": 2,
                    "intervals": [1, 3, 5, 6, 7, 87, 3]
                }).build()

        self.hub_connection.on_open(lambda: print("connection opened and handshake received ready to send messages"))
        self.hub_connection.on_close(lambda: print("connection closed"))
        self.hub_connection.on_error(lambda data: print(f"An exception was thrown closed{data.error}"))
        self.hub_connection.on_reconnect(lambda: print("connection to hub re-established"))
        self.hub_connection.on("ReceiveMessage", print)
        self.hub_connection.on("REQUEST_UPDATE", print)
        
        try:
            self.hub_connection.start()
            print("SignalR Connection Started")
            for i in range(5, 0, -1):
                print(f'Starting in ... {i}')
                time.sleep(1)
            self.hub_connection.send('AddToGroup', [str(self.room_id)])
            print(f'Joined signalR group # {self.room_id}')
        except Exception as e:
            print(e)
    
    def run(self):
        connected = False
        while not connected:
            try:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                # print(">>> connect_and_stream - Room Controller IP Address: " + str(self.extract_ip()))
                print('>>> connect_and_stream - Connecting to last known device IP: ' + str(
                    self.ip_address) + '  MAC: ' + str(self.device_mac) + '  Device Model: ' + str(self.device_model))
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(5.0)
                client_socket.connect((self.ip_address, self.server_port))
                print('>>> connect_and_stream - Connected to ' + str(self.ip_address))
                connected = True

                # writing status update to room_controller_configs file
##                print(">>> connect_and_stream.py - Writing device thread status to configs file ...")
##                with open(self.roomcontroller_configs_file) as configs_file:
##                    initial_file_response = json.load(configs_file)
##                    initial_file_response[f"device_{self.device_mac}_streaming"] = True
##
##                with open(self.roomcontroller_configs_file, "w") as configs_file:
##                    json.dump(initial_file_response, configs_file)



            except socket.error as e:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    client_socket.close()
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                print('>>> connect_and_stream - ' + str(e))
                print('>>> connect_and_stream - The last known IP ' + str(
                    self.ip_address) + ' is no longer valid. Searching network for device... ')
                self.ip_address, self.server_port = self.device_discovery(self.device_mac)  # find new device IP Address
                print('>>> connect_and_stream - Connecting to ' + str(self.ip_address))
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(5.0)
                try:
                    client_socket.connect((self.ip_address, self.server_port))
                    connected = True
                except Exception as e:
                    print('>>> connect_and_stream - ' + str(e))

        try:
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            try:
                # to clear the buffer on NIC when first connect sends MAC.
                data_response_init = client_socket.recvfrom(32)
            except Exception as e:
                print('>>> connect_and_stream - ' + str(e))
                data_response_init = self.device_mac

            data_response_old = None
            print('>>> connect_and_stream - ' + str(self.device_mac) + ' DEVICE CONNECTED AND READY')

            try:
                while True:       
                    if self.device_mac in room_controller.global_active_mac_ids:
                        data_response = (ncd.get_dc_bank_status(0, self.bank_total))
                        data_response_new = data_response

                        if data_response_old != data_response_new:
                            data_response_old = data_response_new

                            # insert SignalR stream
                            try:
                                print('>>> connect_and_stream - SEND VALUES TO CLUEMASTER SignalR > '\
                                      + self.device_mac + ' : ' + str(data_response))
                                self.hub_connection.send('SendMessage', [str(self.device_mac), str(data_response)])
                                self.hub_connection.send('sendtoroom', [str(self.room_id), str(data_response)])
                            except Exception as e:
                                print(e)

                            if log_level in (1, 2):
                                print('>>> connect_and_stream - HEX BYTE VALUES RETURNED FROM DEVICE ' + str(
                                    bytes(data_response)))
                                print('>>> connect_and_stream - LIST VALUES RETURNED FROM DEVICE ' + str(data_response))

                                # make a new array by ignoring the first two bytes and the last byte
                                readings = bytes(data_response)
                                counter = 0
                                bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                                print('>>> connect_and_stream - Binary Response Values : ', bytes_as_bits)

                                # This code block is only for displaying the of/off of the inputs to the log for diagnostics
                                for bank in readings:
                                    # increment through each input
                                    for i in range(0, self.input_total):
                                        # << indicates a bit shift. Basically check corresponding bit in the reading
                                        state = (bank & (1 << i))
                                        if state != 0:
                                            # print('Input '+ str(bank) +' is high')
                                            print('>>> connect_and_stream - BANK Unknown: Input ' + str(
                                                i + 1) + ' is high')
                                        else:
                                            print('>>> connect_and_stream - BANK Unknown: Input ' + str(
                                                i + 1) + ' is low')
                                        counter += 1

                        # wait for a few defined seconds
                        time.sleep(self.read_speed)

                    else:
                        # terminating thread
                        # if just returning doesn't close the thread, try uncommenting client_socket.close()
                        client_socket.close()
                        hub_connection.stop()
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return

            except socket.error:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    client_socket.close()
                    hub_connection.stop()
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                # set connection status and recreate socket
                self.connection_lost()
                self.run()

            except Exception as e:
                #print(">>> connect_and_stream -  Error: " + str(e))
                if self.device_mac not in room_controller.global_active_mac_ids:
                    client_socket.close()
                    hub_connection.stop()
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                return

        except socket.error:
            if self.device_mac not in room_controller.global_active_mac_ids:
                client_socket.close()
                hub_connection.stop()
                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                return
            # set connection status and recreate socket
            self.connection_lost()
            self.run()

        except Exception as e:
            if self.device_mac not in room_controller.global_active_mac_ids:
                client_socket.close()
                hub_connection.stop()
                print(">>> connect_and_stream - Closing Main Thread for " + self.device_mac)
                return
            # set connection status and recreate socket
            print(">>> connect_and_stream -  Error: " + str(e))
            self.connection_lost()
            self.run()

    def connection_lost(self):
        # set connection status and recreate socket
        connected = False
        connect_retry = 0
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1.0)
        try:
            # to clear the buffer on NIC when first connect sends MAC.
            data_response_init = client_socket.recvfrom(32)
        except Exception as e:
            print('>>> connect_and_stream - Connection Lost Error: ' + str(e))
            data_response_init = self.device_mac
        client_socket.close()
        time.sleep(1)
        print('>>> connect_and_stream - connection lost... reconnecting')
        while not connected:
            # attempt to reconnect, otherwise sleep for 30 seconds
            try:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    udp_server_socket.close()
                    print(">>> connect_and_stream - Closing Lost Connection Thread for " + self.device_mac)
                    return
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(1.0)
                client_socket.connect((self.ip_address, self.server_port))
                try:
                    # to clear the buffer on NIC when first connect sends MAC.
                    data_response_init = client_socket.recvfrom(32)
                except Exception as e:
                    print('>>> connect_and_stream - ' + str(e))
                    data_response_init = self.device_mac
                connected = True
                print('>>> connect_and_stream - re-connection successful to ' + str(self.device_mac))
                client_socket.close()
                time.sleep(1)
            except socket.error:
                print(">>> connect_and_stream - " + str(self.device_mac) + ": searching..." + str(connect_retry))
                connect_retry += 1
                if connect_retry == 30:
                    print('>>> connect_and_stream - Connection lost. Starting new search')
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(1.0)
                    try:
                        # to clear the buffer on NIC when first connect sends MAC.
                        data_response_init = client_socket.recvfrom(32)
                    except Exception as e:
                        print('>>> connect_and_stream - ' + str(e))
                        data_response_init = self.device_mac
                    client_socket.close()
                    time.sleep(1)
                    break
##                    try:
##                        self.run()
##                    except SystemExit:
##                        sys.exit(0)
##                    else:
##                        self.run()
##                    finally:
##                        self.run()
##                continue

    def device_discovery(self, device_mac):
        try:
            local_ip = self.extract_ip()
            local_port = 13000
            buffer_size = 1024

            # msgFromServer = "Connected"
            # bytesToSend = str.encode(msgFromServer)

            # Create a datagram socket
            udp_server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            udp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to address and ip
            if platform.system() == "Windows":
                udp_server_socket.bind((local_ip, local_port))
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                # Bind to address and ip
                udp_server_socket.bind(("<broadcast>", local_port))

            # Listen for incoming datagrams
            while True:
                try:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        udp_server_socket.close()
                        print(">>> connect_and_stream - Closing Discovery Thread for " + self.device_mac)
                        return
                    print(">>> connect_and_stream - " + str(datetime.datetime.utcnow()) + " - UDP Network Search for: " + str(device_mac))
                    udp_server_socket.settimeout(15)
                    bytes_address_pair = udp_server_socket.recvfrom(buffer_size)

                    if log_level in (1, 3):
                        print(bytes_address_pair)
                        print(list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))
                    # data returned# ['192.168.1.19', '0008DC21DDFD', '2101', 'NCD.IO', '2.4 (IP, PORT)
                    # \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
                    # \\x00\\x00\\x00\\x00\\x00']

                    discover_ip = ((bytes_address_pair[1])[0])
                    discover_mac = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[1]
                    discover_port = \
                        int((list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[2])
                    # We are using the model from the json file for now
                    # discovery_model = \
                    #     (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[3]
                    discovery_version = \
                        (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[4]
                    discover_model = self.device_model
                    discover_device_type = self.device_type

                    if discover_mac == self.device_mac:
                        try:
                            print(">>> connect_and_stream - Discovered Device IP:  ", discover_ip)
                            print(">>> connect_and_stream - Discovered Device MAC: ", discover_mac)
                            print(">>> connect_and_stream - Discovered Device Port: ", discover_port)
                            print(">>> connect_and_stream - Discovered Device Model: ", discover_model)
                            print(">>> connect_and_stream - Discovered Device Type: ", discover_device_type)
                            print(">>> connect_and_stream - Discovered Device Network Card Firmware Version: ",
                                  discovery_version)
                            print(">>> connect_and_stream - Saving updated device info to file.")
                            self.save_device_info(discover_ip, discover_mac, discover_port)
                            self.update_webapp_with_new_details(ip_address=discover_ip, macaddress=discover_mac,
                                                                serverport=discover_port)

                            udp_server_socket.close()
                            time.sleep(1)
                            break
                        except Exception as e:
                            print(">>> connect_and_stream - Error: Unable to save updated device info to file.")
                            print('>>> connect_and_stream - ' + str(e))
                    else:
                        if self.device_mac not in room_controller.global_active_mac_ids:
                            udp_server_socket.close()
                            print(">>> connect_and_stream - Closing Discovery Thread for " + self.device_mac)
                            return
                        print(">>> connect_and_stream - " + str(datetime.datetime.utcnow()) + " - Device: " + str(
                            device_mac) + " not found on network. Continuing to search...")

                    # break
                except socket.error:  # change to exception:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        udp_server_socket.close()
                        print(">>> connect_and_stream - Closing Discovery Thread for " + self.device_mac)
                        return
                    print(">>> connect_and_stream - UDP Search Timeout Reached - Device not found")
                    # set connection status and recreate socket
                    #self.device_discovery(device_mac)
                    #self.run()

        except Exception as e:
            if self.device_mac not in room_controller.global_active_mac_ids:
                udp_server_socket.close()
                print(">>> connect_and_stream - Closing Discovery Thread for " + self.device_mac)
                return
            print('>>> connect_and_stream - ' + str(e))
            print(">>> connect_and_stream - Error trying to open UDP discovery port")
            # set connection status and recreate socket
            #self.connection_lost()
            #self.run()

        return discover_ip, discover_port

    @staticmethod
    def extract_ip():
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            st.connect(('10.255.255.255', 1))
            ip_address = st.getsockname()[0]
        except socket.error:
            ip_address = '127.0.0.1'
            print(">>> connect_and_stream - Error trying to find Room Controller IP, Defaulting to 127.0.0.1")
        except Exception:
            ip_address = '127.0.0.1'
            print(">>> connect_and_stream - Error trying to find Room Controller IP, Defaulting to 127.0.0.1")
        finally:
            st.close()
        return ip_address

    @staticmethod
    def reboot_device():
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            try:
                data_response_init = client_socket.recvfrom(32)
                print(str(data_response_init))
                # to clear the buffer on NIC when first connect sends MAC.
            except Exception as e:
                print('>>> connect_and_stream - ' + str(e))
                # data_response_init = self.device_mac
            ncd.device_reboot()
            client_socket.close()
            print(">>> connect_and_stream - Device Rebooted")

        except Exception:
            print(">>> connect_and_stream - Error Sending Reboot Command")

    @staticmethod
    def save_device_info(ip, i_mac, port):
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        with open(device_info_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)
            for device in connected_devices_file_response["Devices"]:
                if device["MacAddress"] == i_mac:
                    print(f">>> connect_and_stream - Updating IP and PORT of {i_mac} in JSON file.")
                    device["IP"] = str(ip)
                    device["ServerPort"] = int(port)

        with open(device_info_file, "w") as connected_devices_file:
            json.dump(connected_devices_file_response, connected_devices_file)

    @staticmethod
    def read_device_info(i_mac):
        try:
            device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
            with open(device_info_file) as connected_devices_file:
                connected_devices_file_response = json.load(connected_devices_file)
                for values in connected_devices_file_response["Devices"]:
                    device_mac_address = values["MacAddress"]
                    if device_mac_address == i_mac:
                        print(">>> connect_and_stream - Device record exists for : ", i_mac)
                        return values["IP"], values["ServerPort"], values["DeviceModel"], values["DeviceType"], values[
                            "ReadSpeed"], values["InputTotal"], values["RelayTotal"], values["RoomID"]
                        exit()

        except Exception as e:
            print('>>> connect_and_stream - ' + str(e))
            print(">>> connect_and_stream - device_info file does not exist or there is improperly formatted data")

    def update_webapp_with_new_details(self, ip_address, macaddress, serverport):
        with open(os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")) as unique_ids_file:
            unique_ids_file_response = json.load(unique_ids_file)

        device_unique_id = unique_ids_file_response["device_id"]
        api_bearer_key = unique_ids_file_response["api_token"]

        api_header = CaseInsensitiveDict()
        api_header["Authorization"] = f"Basic {device_unique_id}:{api_bearer_key}"
        api_header['Content-Type'] = 'application/json'
        updated_data = [{"IP": ip_address, "ServerPort": str(serverport), "MacAddress": macaddress}]

        print(">>> add_find_device - PostNewInputRelayRequestUpdate sending: " + str(updated_data))

        try:
            response = requests.post(self.post_input_relay_request_update_api, headers=api_header,
                                     data=json.dumps(updated_data))
        except Exception as api_error:
            print(">>> connect_and_stream - Error: " + str(api_error))
        else:
            print(">>> add_find_device - PostNewInputRelayRequestUpdate response : ", response.status_code)
            print(">>> add_find_device - PostNewInputRelayRequestUpdate response text : ", response.text)

# Comment out the function when testing from main.py

##def start_thread():
##    if __name__ == "__main__":
##        connect_and_stream_instance = ConnectAndStream(device_mac="0008DC21DDF0")
##        # enter hardcoded MAC  and enter sped in milliseconds to query data from the device
##        connect_and_stream_instance.start()
##
##
##start_thread()
