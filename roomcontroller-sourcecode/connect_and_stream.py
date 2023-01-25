import json
import threading
import socket
import time
import datetime
import os
import platform
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
        self.api_headers = None
        self.device_request_api_url = None
        self.api_bearer_key = None
        self.device_unique_id = None
        self.handler = None
        self.server_url = None
        self.hub_connection = None
        self.data_response = None
        self.active = None
        print(">>> connect_and_stream - GLOBAL MAC: ", room_controller.global_active_mac_ids)
        self.device_mac = device_mac
        [self.ip_address, self.server_port, self.device_model, self.device_type, self.read_speed, self.input_total,
         self.relay_total, self.room_id] = self.read_device_info(self.device_mac)
        self.bank_total = ((self.input_total // 8) - 1)
        self.post_input_relay_request_update_api = POST_INPUT_RELAY_REQUEST_UPDATE
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.signalr_status = None
        self.client_socket = None
        self.ncd = None

        # instance methods
        self.configuration()
        self.signalr_hub()
        print(">>> connect_and_stream - STARTUP COMPLETED")

    def configuration(self):
        with open(self.unique_ids_file) as unique_ids_file:
            json_response_of_unique_ids_file = json.load(unique_ids_file)

        self.device_unique_id = json_response_of_unique_ids_file["device_id"]
        self.api_bearer_key = json_response_of_unique_ids_file["api_token"]
        self.device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

        self.api_headers = CaseInsensitiveDict()
        self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"

    def signalr_hub(self):
        self.server_url = API_SIGNALR
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.ERROR)
        self.hub_connection = HubConnectionBuilder() \
            .with_url(self.server_url, options={
                "verify_ssl": True,
                "skip_negotiation": False,
                "http_client_options": {"headers": self.api_headers, "timeout": 5.0},
                "ws_client_options": {"headers": self.api_headers, "timeout": 5.0},
            }) \
            .configure_logging(logging.ERROR, socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect({
                "type": "raw",
                "keep_alive_interval": 5,
                "reconnect_interval": 5,
                "max_attempts": 99999999
                # "type": "interval",
                # "keep_alive_interval": 5,
                # "reconnect_interval": 5,
                # "max_attempts": 99999999,
                # "intervals": [1, 3, 5, 6, 7, 87, 3]
            }).build()

        self.hub_connection.on_close(lambda: (print(">>> connect_and_stream - SignalR Connection Closed")))
        self.hub_connection.on_error(lambda data: print(f">>> connect_and_stream - An exception was thrown:"
                                                        f"{data.error}"))
        self.hub_connection.on_open(lambda: (self.hub_connection.send('AddToGroup', [str(self.room_id)]), print(
            ">>> connect_and_stream - signalR handshake received. Ready to send/receive messages."),
                                             self.signalr_connected()))
        self.hub_connection.on_reconnect(lambda: (print(">>> connect_and_stream - Trying to re-connect to "
                                                        "comhub.cluemaster.io")))
        self.hub_connection.on(str(self.room_id), print)
        self.hub_connection.on('syncdata', (lambda data: self.hub_connection.send(
            'sendtoroom', [str(self.room_id), str(self.device_mac), str(self.data_response)])))
        self.hub_connection.on('syncdata', (lambda data: print(">>> connect_and_stream - "
                                                               "Re-Sync Data command received")))

        self.hub_connection.start()

        while self.signalr_status is not True:
            for i in range(15, -1, -1):
                if self.signalr_status is True:
                    break
                if i == 0:
                    print(f'>>> connect_and_stream - timeout exceeded. SignalR not connected.')
                    break
                print(f'>>> connect_and_stream - waiting for signalR handshake ... {i}')
                time.sleep(1)
            break
        else:
            print(">>> connect_and_stream - signalr connected")

    def signalr_connected(self):
        self.signalr_status = True

    def run(self):
        connected = False
        while not connected:
            try:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                # print(">>> connect_and_stream - Room Controller IP Address: " + str(self.extract_ip()))
                print('>>> connect_and_stream - Connecting to last known device IP: ', self.ip_address, '  MAC: ',
                      self.device_mac, '  Device Model: ', self.device_model)
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(1.0)
                self.client_socket.connect((self.ip_address, self.server_port))
                print('>>> connect_and_stream - Connected to IP:', self.ip_address, ' MAC:', self.device_mac)
                connected = True

            except socket.error as e:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    self.client_socket.close()
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))
                print('>>> connect_and_stream - The last known IP ' + str(
                    self.ip_address) + ' is no longer valid. Searching network for device... ')
                self.ip_address, self.server_port = self.device_discovery(self.device_mac)  # find new device IP Address
                print('>>> connect_and_stream - Connecting to ' + str(self.ip_address))
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(1.0)
                try:
                    self.client_socket.connect((self.ip_address, self.server_port))
                    connected = True
                except Exception as e:
                    print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))

            self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)
            # self.hub_connection.on('device_reboot', str(self.device_mac),
            #                        (lambda relay_num: (self.ncd.device_reboot())))
            # self.hub_connection.on(str(self.room_id), (lambda relay_num: (self.ncd.turn_on_relay_by_bank(1, 2))))
            # self.hub_connection.on(str(self.room_id), (lambda relay_num: (self.ncd.turn_off_relay_by_bank(1, 2))))

        try:
            self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)
            try:
                # to clear the buffer on NIC when first connect sends MAC.
                data_response_init = self.client_socket.recvfrom(32)
            except Exception as e:
                print('>>> connect_and_stream - init ERROR: ' + str(e))
                data_response_init = self.device_mac

            data_response_old = None

            print('>>> connect_and_stream - ', self.device_mac, ' DEVICE CONNECTED AND READY')

            while self.device_mac in room_controller.global_active_mac_ids:
                # print("start processing loop")
                try:
                    # while self.device_mac in room_controller.global_active_mac_ids:

                    if self.device_type == 2:
                        # print("IM WAITING FORE RELAY COMMANDS")
                        # loop here and do nothing but check for connection to the relay board.
                        # signalR will fire in the background when needed.
                        # while self.device_mac in room_controller.global_active_mac_ids:
                        # try:
                        #     self.ncd.test_comms()
                        # except Exception as e:
                        #     print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))
                        self.ncd.test_comms()
                        time.sleep(1)

                    elif self.device_type == 1:

                        self.data_response = (self.ncd.get_dc_bank_status(0, self.bank_total))
                        data_response_new = self.data_response
                        if not self.data_response:
                            print(f'DATA RESPONCE IS: {self.data_response}')

                        if data_response_old != data_response_new:
                            data_response_old = data_response_new

                            if self.signalr_status:
                                # insert SignalR stream
                                try:
                                    print('>>> connect_and_stream - SEND VALUES TO CLUEMASTER SignalR > '
                                          , [str(self.room_id), str(self.device_mac), str(self.data_response)])
                                    self.hub_connection.send('sendtoroom', [str(self.room_id), str(self.device_mac),
                                                                            str(self.data_response)])
                                except Exception as e:
                                    print(f'>>> connect_and_stream - {self.device_mac} Connection Error: {e}')
                            else:
                                print('>>> connect_and_stream - SIGNALR IS NOT CONNECTED > '
                                      , [str(self.room_id), str(self.device_mac), str(self.data_response)])

                            # if log_level in (1, 2):
                            #     print('>>> connect_and_stream - HEX BYTE VALUES RETURNED FROM DEVICE ',
                            #           str(bytes(self.data_response)))
                            #     print('>>> connect_and_stream - LIST VALUES RETURNED FROM DEVICE ',
                            #           str(self.data_response))
                            #
                            #     # make a new array by ignoring the first two bytes and the last byte
                            #     readings = bytes(self.data_response)
                            #     counter = 0
                            #     bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                            #     print('>>> connect_and_stream - Binary Response Values : ', bytes_as_bits)
                            #
                            #     # This code block is only for displaying the of/off of the inputs to the log for
                            #     # diagnostics
                            #     for bank in readings:
                            #         # increment through each input
                            #         for i in range(0, self.input_total):
                            #             # << indicates a bit shift. Basically check corresponding bit in the reading
                            #             state = (bank & (1 << i))
                            #             if state != 0:
                            #                 # print('Input '+ str(bank) +' is high')
                            #                 print('>>> connect_and_stream - BANK Unknown: Input ' + str(
                            #                     i + 1) + ' is high')
                            #             else:
                            #                 print('>>> connect_and_stream - BANK Unknown: Input ' + str(
                            #                     i + 1) + ' is low')
                            #             counter += 1

                        # wait for a few defined seconds
                        time.sleep(self.read_speed * 0.001)

                    else:
                        # terminating thread
                        try:
                            self.client_socket.close()
                            self.hub_connection.stop()
                        except Exception as error:
                            print('>>> connect_and_stream - ', self.device_mac, ' Error: ', str(error))
                        print(">>> connect_and_stream - Device Type Not Compatible")
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return

                except socket.error:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        try:
                            self.client_socket.close()
                            self.hub_connection.stop()
                        except Exception as error:
                            print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(error))
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return
                    # set connection status and recreate socket
                    connected = False
                    while not connected:
                        try:
                            if self.device_mac not in room_controller.global_active_mac_ids:
                                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                                return
                            self.client_socket.close()
                            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.client_socket.settimeout(1.0)
                            self.client_socket.connect((self.ip_address, self.server_port))

                            # Verify communication and clear nic buffer to get rid of FALSE response
                            self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)

                            try:
                                # to clear the buffer on NIC when first connect sends MAC.
                                self.client_socket.recvfrom(32)
                            except Exception as e:
                                print('>>> connect_and_stream - ', self.device_mac, ' Socket Buffer Error: ', str(e))

                            self.ncd.test_comms()
                            print('>>> connect_and_stream - Connected to IP:', self.ip_address, ' MAC:',
                                  self.device_mac)
                            connected = True

                        except socket.error as e:
                            if self.device_mac not in room_controller.global_active_mac_ids:
                                self.client_socket.close()
                                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                                return
                            print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))
                            self.connection_lost()

                except Exception as e:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        try:
                            self.client_socket.close()
                            self.hub_connection.stop()
                        except Exception as error:
                            print(f'>>> connect_and_stream - {error}')
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return
                    print(">>> connect_and_stream -  Error: " + str(e))

            try:
                self.client_socket.close()
                self.hub_connection.stop()
            except Exception as error:
                print(f'>>> connect_and_stream - {error}')
            print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
            return

        except socket.error:
            if self.device_mac not in room_controller.global_active_mac_ids:
                try:
                    self.client_socket.close()
                    self.hub_connection.stop()
                except Exception as error:
                    print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(error))
                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                return
            # set connection status and recreate socket
            connected = False
            while not connected:
                try:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return
                    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client_socket.settimeout(1.0)
                    self.client_socket.connect((self.ip_address, self.server_port))

                    # Verify communication and clear nic buffer to get rid of FALSE response
                    self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)

                    try:
                        # to clear the buffer on NIC when first connect sends MAC.
                        self.client_socket.recvfrom(32)
                    except Exception as e:
                        print('>>> connect_and_stream - ', self.device_mac, ' Socket Buffer Error: ', str(e))

                    self.ncd.test_comms()
                    print('>>> connect_and_stream - Connected to IP:', self.ip_address, ' MAC:',
                          self.device_mac)
                    connected = True

                except socket.error as e:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        self.client_socket.close()
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return
                    print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))
                    self.connection_lost()

        except Exception as e:
            if self.device_mac not in room_controller.global_active_mac_ids:
                try:
                    self.client_socket.close()
                    self.hub_connection.stop()
                except Exception as error:
                    print(error)
                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                return

    def connection_lost(self):
        # set connection status and recreate socket
        connected = False
        connect_retry = 15
        # self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.client_socket.settimeout(1.0)
        # try:
        #     # to clear the buffer on NIC when first connect sends MAC.
        #     self.client_socket.recvfrom(32)
        # except Exception as e:
        #     print('>>> connect_and_stream - Connection Lost Error: ' + str(e))
        #     # data_response_init = self.device_mac
        # self.client_socket.close()
        # time.sleep(1)
        print('>>> connect_and_stream - connection lost... reconnecting')
        while not connected:
            # attempt to reconnect, otherwise loop for 15 seconds
            try:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    self.client_socket.close()
                    print(">>> connect_and_stream - Closing Lost Connection Thread for " + self.device_mac)
                    return
                self.client_socket.close()
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(1.0)
                self.client_socket.connect((self.ip_address, self.server_port))
                # try:
                #     # to clear the buffer on NIC when first connect sends MAC.
                #     self.client_socket.recvfrom(32)
                # except Exception as e:
                #     print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))

                connected = True
                print('>>> connect_and_stream - re-connection successful to ' + str(self.device_mac))
                self.client_socket.close()
                time.sleep(1)
            except socket.error:
                print(">>> connect_and_stream - " + str(self.device_mac) + ": searching..." + str(connect_retry))
                connect_retry -= 1
                if connect_retry == 0:
                    print('>>> connect_and_stream - Connection Lost. Starting Network Discovery Search')
                    self.device_discovery(self.device_mac)
                    time.sleep(1)
                    break

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
                    print(">>> connect_and_stream - " + str(
                        datetime.datetime.utcnow()) + " - UDP Network Search for: " + str(device_mac))
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
                    # self.device_discovery(device_mac)
                    # self.run()

            # print("done with discovery loop")

        except Exception as e:
            if self.device_mac not in room_controller.global_active_mac_ids:
                udp_server_socket.close()
                print(">>> connect_and_stream - Closing Discovery Thread for " + self.device_mac)
                return
            print('>>> connect_and_stream - ' + str(e))
            print(">>> connect_and_stream - Error trying to open UDP discovery port")
            # set connection status and recreate socket
            # self.connection_lost()

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

        except socket.error:
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
                        # exit()

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
