import os
import json
import platform
import socket
import threading
import time
import requests
import dbus

import websocket
from requests.structures import CaseInsensitiveDict

# import the python scripts
from apis import *
import connect_and_stream
import add_find_device
import heartbeat
import connected_devices
import websocket_server

# This import will be for signalR code##
import logging
from signalrcore.hub_connection_builder import HubConnectionBuilder
from signalrcore.protocol.messagepack_protocol import MessagePackHubProtocol

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# global variables
# global global_active_mac_ids
global_active_mac_ids = []

# global ACTIVE_INPUT_VALUES
ACTIVE_INPUT_VALUES = []

# global GLOBAL_AUTOMATION_RULE_PENDING
GLOBAL_AUTOMATION_RULE_PENDING = None

# global GLOBAL_GAME_STATUS
GLOBAL_GAME_STATUS = None

# global GLOBAL_GAME_STATUS
# GLOBAL_GAME_COMMAND: list = []

# global GLOBAL_DEVICE_UNIQUE_ID
GLOBAL_DEVICE_UNIQUE_ID = None

# global GLOBAL_ROOM_ID
# GLOBAL_ROOM_ID = None

GLOBAL_IP = None


# master class
class RoomController:
    def __init__(self):
        super(RoomController, self).__init__()

        # local class attributes
        self.room_id = None
        self.signalr_bearer_token = None
        # self.device_request_api_url = None
        self.api_bearer_key = None
        self.get_automationrule_request_api = None
        self.get_automationrule_api = None
        self.hub_connection = None
        self.handler = None
        self.server_url = None
        self.active_mac_ids = []
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.discover_new_relays_request_api = None
        self.get_devicelist_api = None
        self.post_roomcontroller_request_api = None
        self.get_roomcontroller_request_api = None
        self.restart_rc_id = 8
        self.shutdown_rc_id = 9
        self.search_for_devices_id = 12
        self.update_device_list_id = 13
        self.update_automation_rule_id = 14
        self.resetting_room_controller = False
        self.connect_and_stream_thread = None
        self.heartbeat_thread = None
        self.add_find_device_thread = None
        self.get_devicelist_request_api = None
        self.signalr_status = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found",
                                          "No record found in inventory master"]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.automation_rules_file = os.path.join(APPLICATION_DATA_DIRECTORY, "automation_rules.json")

        # instance methods
        self.configurations()
        # self.signalr_hub()
        print(">>> room_controller - **********  STARTUP COMPLETE  **********")

        self.heartbeat_thread = HeartbeatThread()
        self.heartbeat_thread.start()

        self.WebsocketServer_thread = WebsocketServerThread()
        self.WebsocketServer_thread.start()

        self.execution_environment()
        print(">>> room_controller - **********  ROOM CONTROLLER SHUTTING DOWN  **********")
        heartbeat.HEARTBEAT_STOP = True
        print(">>> room_controller - **********  STOPPING HEARTBEAT THREAD  **********")
        websocket_server.WEBSOCKETSERVER_STOP = True
        print(">>> room_controller - **********  STOPPING WEBSOCKET_SERVER THREAD  **********")

    def configurations(self):
        try:
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            self.device_unique_id = json_response_of_unique_ids_file["device_id"]
            self.set_device_unique_id(self.device_unique_id)
            self.api_bearer_key = json_response_of_unique_ids_file["api_token"]
            # self.device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

            self.api_headers = CaseInsensitiveDict()
            self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"
            self.signalr_bearer_token = f"?access_token={self.device_unique_id}_{self.api_bearer_key}"
            # self.signalr_access_token = f'?access_token=1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt'

            # GET API
            self.discover_new_relays_request_api = NEW_RELAYS_DISCOVERY_REQUEST.format(device_id=self.device_unique_id)
            self.get_devicelist_request_api = GET_NEW_INPUT_RELAY_LIST_REQUEST.format(device_id=self.device_unique_id)
            self.get_devicelist_api = GET_NEW_INPUT_RELAY_LIST.format(device_id=self.device_unique_id)
            self.get_automationrule_api = GET_ROOM_AUTOMATION_MASTER.format(device_id=self.device_unique_id)
            self.get_automationrule_request_api = GET_ROOM_CONTROLLER_AUTOMATION_REQUEST.format(device_id=self.device_unique_id)
            self.get_roomcontroller_request_api = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

            # load room id into memory
            self.get_rc_room_id()

            # load all the devices on startup into memory array
            self.init_previous_devices()
            self.init_automation_rules()

        except Exception as ErrorFileNotFound:
            print(f'>>> room_controller - Error: {ErrorFileNotFound}')

    def execution_environment(self):
        while True:
            try:
                # Try to Connect to Comhub with SignalR and loop until it does.
                if self.signalr_status is not True:
                    try:
                        self.signalr_hub()
                    except Exception as error:
                        print(f">>> room_controller - {self.device_unique_id} - SignalR Did not connect for Room "
                              f"Controller. Server Error: {error}")
                        # time.sleep(5)

                # print(">>> Console Output " + str(datetime.datetime.utcnow()) +
                # " - Searching for new input relays request ...")
                relays_discovery_request = requests.get(self.discover_new_relays_request_api, headers=self.api_headers)
                # print(">>> room_controller - " + str(datetime.datetime.utcnow()) +
                # "Waiting for code 12,13 : " + relays_discovery_request.text)
                relays_discovery_request.raise_for_status()

                if relays_discovery_request.text not in self.api_active_null_responses:
                    request_id = relays_discovery_request.json()["RequestID"]

                    if request_id == self.search_for_devices_id:
                        print(">>> room_controller - Acknowledging request for Input Relay with RequestId ", request_id)
                        self.post_roomcontroller_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                                   request_id=request_id)
                        requests.post(self.post_roomcontroller_request_api, headers=self.api_headers)

                        # staring add_find_device thread
                        self.start_add_find_device_thread(response=relays_discovery_request.json())
                    else:
                        print(">>> room_controller - Unexpected Request id:", str(request_id), "returned.")

                time.sleep(1)

                # Looking for DeviceRequest ID's 8,9
                get_roomcontroller_request = requests.get(self.get_roomcontroller_request_api, headers=self.api_headers)

                # "Waiting for code 8,9
                get_roomcontroller_request.raise_for_status()

                if get_roomcontroller_request.text not in self.api_active_null_responses:
                    request_id = get_roomcontroller_request.json()["RequestID"]
                    print(f">>> room_controller - {time.ctime()} + {get_roomcontroller_request} "
                          f"+ REQUEST_ID: {request_id}")

                    if request_id == self.restart_rc_id:
                        print(">>> room_controller - Acknowledging request for Input Relay with RequestId ", request_id)
                        self.post_roomcontroller_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                                   request_id=request_id)
                        # Acknowledge request ID back to API to confirm receipt.
                        requests.post(self.post_roomcontroller_request_api, headers=self.api_headers)

                        # Restart the Room Controller SNAP
                        self.restart_rc()

                    elif request_id == self.shutdown_rc_id:
                        print(">>> room_controller - Acknowledging request for Input Relay with RequestId ", request_id)
                        self.post_roomcontroller_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                                   request_id=request_id)
                        requests.post(self.post_roomcontroller_request_api, headers=self.api_headers)

                        # Shutdown the Room Controller Device
                        self.shutdown_rc()

                    else:
                        print(">>> room_controller - Unexpected Request id:", str(request_id), "returned.")

                time.sleep(1)

                # looking for new request to download the latest AutomationRules File
                get_automationrule_request = requests.get(self.get_automationrule_request_api, headers=self.api_headers)
                get_automationrule_request.raise_for_status()

                if get_automationrule_request.text not in self.api_active_null_responses:
                    request_id = get_automationrule_request.json()["RequestID"]

                    if request_id == self.update_automation_rule_id:
                        print(">>> room_controller - Acknowledging request to GET new updated Automation Rule with RequestId ", request_id)

                        self.post_roomcontroller_request_api = POST_ROOM_CONTROLLER_REQUEST.format(
                            device_id=self.device_unique_id,
                            request_id=request_id)
                        requests.post(self.post_roomcontroller_request_api, headers=self.api_headers)
                        # print(requests.post(self.general_request_api, headers=self.api_headers))

                        # download latest list of devices from ClueMaster to refresh list if request_id=14
                        print(">>> room_controller - Download new Automation File form ClueMaster")
                        get_automationrule_response = self.get_automationrules_file()
                        print(f">>> room_controller - Update automation_rules.JSON file")
                        self.save_automationrules_file(get_automationrule_response)

                        # Set global var to true to relay threads can update rules in memory without rebooting
                        global GLOBAL_AUTOMATION_RULE_PENDING
                        GLOBAL_AUTOMATION_RULE_PENDING = True

                time.sleep(1)

                # looking for new request to download the latest devices' info, after AddFindDevice thread...
                get_devicelist_request = requests.get(self.get_devicelist_request_api, headers=self.api_headers)
                get_devicelist_request.raise_for_status()

                if get_devicelist_request.text not in self.api_active_null_responses:
                    request_id = get_devicelist_request.json()["RequestID"]

                    if request_id == self.update_device_list_id:
                        print(
                            ">>> room_controller - Acknowledging request to GET new updated list of devices with RequestId ",
                            request_id)
                        # self.general_request_api = POST_INPUT_RELAY_REQUEST_UPDATE.format(device_id=self.device_unique_id, request_id=request_id)
                        # requests.post(self.general_request_api, headers=self.api_headers)

                        self.post_roomcontroller_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                                   request_id=request_id)
                        requests.post(self.post_roomcontroller_request_api, headers=self.api_headers)
                        # print(requests.post(self.general_request_api, headers=self.api_headers))

                        # download latest list of devices from ClueMaster to refresh list if request_id=13
                        print(">>> room_controller - Download new device list form ClueMaster")
                        get_devicelist_response = self.get_devicelist()
                        print(">>> room_controller - Update Connected_Devices.JSON file")
                        self.save_device_info(get_devicelist_response)

                        # handling new devices added
                        new_devices_added = list(self.handling_devices_info())
                        if new_devices_added is not None:
                            for device in new_devices_added:
                                print(">>> room_controller -", str(device), "Starting up.....")
                                self.connect_and_stream_data(device_mac_id=device)
                        else:
                            print(">>> room_controller - Unexpected Request id:", str(request_id), "returned.")

                # print("Sleep 3")
                time.sleep(3)

            except requests.exceptions.ConnectionError:
                # sleep for 5 sec before trying again
                print(">>> room_controller - room_controller.py API Connection Error. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            except requests.exceptions.HTTPError as request_error:
                if "401 Client Error" in str(request_error):
                    self.reset_room_controller()
                    time.sleep(5)
                    break
                else:
                    print(">>> room_controller - " + str(request_error))
                    time.sleep(5)

            except requests.exceptions.JSONDecodeError as json_error:
                print(">>> room_controller - room_controller.py JsonDecodeError")
                print(">>> room_controller - Error ", str(json_error))
                time.sleep(5)
                pass

            except KeyboardInterrupt:
                print(">>> room_controller - room_controller.py Keyboard Interrupt")
                break

    def start_add_find_device_thread(self, response):
        if response["IpAddress"] != '':
            ip_address = response["IpAddress"]
            mac_address = response["macaddress"]
            server_port = response["server_port"]

            self.add_find_device_thread = add_find_device.AddFindDevices(method='add', ip=ip_address,
                                                                         server_port=server_port,
                                                                         mac_address=mac_address)
            self.add_find_device_thread.start()
        else:
            self.add_find_device_thread = add_find_device.AddFindDevices(method='find')
            self.add_find_device_thread.start()

    def get_rc_room_id(self):
        try:
            # Get Room Controller Room number it's assigned to
            room_id_api_url = GET_ROOM_CONTROLLER_INFO_API.format(device_id=self.device_unique_id)
            json_response_of_room_id_api = requests.get(room_id_api_url, headers=self.api_headers).json()
            self.room_id = json_response_of_room_id_api["RoomID"]
            # set the Room ID for the Room Controller to listen to signalR commands

            print(f">>> room_controller - {self.device_unique_id} - Room Controller RoomID: {self.room_id}")

            # update room controller configuration file with new room id value
            with open(self.roomcontroller_configs_file) as configurations_file:
                configurations_file_data = json.load(configurations_file)

            with open(self.roomcontroller_configs_file, "w") as configurations_file:
                configurations_file_data["room_id"] = self.room_id
                json.dump(configurations_file_data, configurations_file)

        except Exception as error:
            # can't query api
            print(f">>> room_controller - {self.device_unique_id} - ERROR, Unable to query api for Room ID. "
                  f"Setting to previously saved Room ID.")
            with open(self.roomcontroller_configs_file) as configurations_file:
                configurations_file_data = json.load(configurations_file)
                self.room_id = configurations_file_data["room_id"]


    def get_devicelist(self):
        print(">>> room_controller - API query to download new list of devices")
        get_devicelist = requests.get(self.get_devicelist_api, headers=self.api_headers).json()
        print(">>> room_controller - New devices info : ", get_devicelist)
        return get_devicelist

    def get_automationrules_file(self):
        print(">>> room_controller - API query to download new Automation Rules file.")
        get_automationrules = requests.get(self.get_automationrule_api, headers=self.api_headers).json()
        print(">>> room_controller - New devices info : ", get_automationrules)
        return get_automationrules

    # @staticmethod
    def save_device_info(self, api_json_list):
        # device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        device_info_dict = {"Devices": api_json_list}

        with open(self.connected_devices_file, "w") as device_info:
            json.dump(device_info_dict, device_info)

    def save_automationrules_file(self, api_json_list):
        with open(self.automation_rules_file, "w") as automation_file:
            json.dump(api_json_list, automation_file)

    def handling_devices_info(self):
        devices_mac_ids = []
        new_devices = []

        with open(self.connected_devices_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)

            for devices in connected_devices_file_response["Devices"]:
                devices_mac_ids.append(devices["MacAddress"])

        print(">>> room_controller - Current In Memory Device List : " + str(self.active_mac_ids))
        print(">>> room_controller - Updated Connected Device File : " + str(devices_mac_ids))

        for device in list(devices_mac_ids):
            if device in self.active_mac_ids:
                print(">>> room_controller - Device ", str(device), " already loaded in memory, skipping")
                pass
            else:
                new_devices.append(device)
                print(">>> room_controller - Device ", str(device), "found and added")

        self.active_mac_ids = devices_mac_ids
        print(">>> room_controller - Updating GV - In Memory Device List : " + str(self.active_mac_ids))
        # os.environ['Registered_Devices'] = str(self.active_mac_ids)
        # print(">>> room_controller - Updating ENV VAR - In Memory Device List", os.environ.get('Registered_Devices'))
        global global_active_mac_ids
        global_active_mac_ids = self.active_mac_ids

        return new_devices

    def init_previous_devices(self):
        try:
            with open(self.connected_devices_file) as connected_devices_file:
                connected_devices_file_response = json.load(connected_devices_file)

                for devices in connected_devices_file_response["Devices"]:
                    self.active_mac_ids.append(devices["MacAddress"])

        except Exception as ErrorFileNotFound:
            print(f'>>> room_controller - Error: {ErrorFileNotFound}')
            api_json_list = self.get_devicelist()
            print(f'>>> room_controller - Creating new connected_devices_file')
            self.save_device_info(api_json_list)

            with open(self.connected_devices_file) as connected_devices_file:
                connected_devices_file_response = json.load(connected_devices_file)

                for devices in connected_devices_file_response["Devices"]:
                    self.active_mac_ids.append(devices["MacAddress"])

            print(">>> room_controller - connected_devices.json file created and loaded into memory")

        print(">>> room_controller - Loading Previously Connected Devices into Global Variable: " + str(
            self.active_mac_ids))

        global global_active_mac_ids
        global_active_mac_ids = self.active_mac_ids

        connected_devices.ConnectedDevices()

    def init_automation_rules(self):
        try:
            # download latest list of devices from ClueMaster to refresh list if request_id=14
            print(">>> room_controller - Download new Automation File form ClueMaster")
            get_automationrule_response = self.get_automationrules_file()
            print(f">>> room_controller - Update automation_rules.JSON file")
            self.save_automationrules_file(get_automationrule_response)

            # Set global var to true to relay threads can update rules in memory without rebooting
            global GLOBAL_AUTOMATION_RULE_PENDING
            GLOBAL_AUTOMATION_RULE_PENDING = True
        except Exception as error:
            print(f">>> room_controller - Automation File Download Error: {error}")

    def connect_and_stream_data(self, device_mac_id):
        print(">>> room_controller - Starting ConnectAndStream thread for device - ", device_mac_id)
        self.connect_and_stream_thread = connect_and_stream.ConnectAndStream(device_mac=device_mac_id)
        self.connect_and_stream_thread.start()

    def signalr_hub(self):
        self.server_url = API_SIGNALR + self.signalr_bearer_token
        print(f">>> room_controller - {self.device_unique_id} - SignalR connected to {API_SIGNALR}")
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.CRITICAL)
        self.hub_connection = HubConnectionBuilder() \
            .with_url(self.server_url, options={
            "verify_ssl": True,
            "skip_negotiation": False
        }) \
            .configure_logging(logging.CRITICAL, socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect({
            "type": "raw",
            "keep_alive_interval": 5,
            "reconnect_interval": 10,
            "max_attempts": 99
        }).build()
        # TODO try to get retries working and connect to signalR when online
        # "accessTokenFactory": 'value'
        # "http_client_options": {"headers": self.api_headers, "timeout": 5.0},
        # "ws_client_options": {"headers": self.api_headers, "timeout": 5.0}
        # "type": "raw",
        # "type": "interval",
        # "keep_alive_interval": 5,
        # "reconnect_interval": 5,
        # "max_attempts": 99999999,
        # "intervals": [1, 3, 5, 6, 7, 87, 3]
        # .with_hub_protocol(MessagePackHubProtocol()) \

        self.hub_connection.on_close(lambda: (print(f">>> room_controller - {self.device_unique_id} - SignalR "
                                                    f"Connection Closed"), self.signalr_connected(False)
                                              ))
        self.hub_connection.on_error(lambda data: (print(f">>> room_controller - {self.device_unique_id} - "
                                                         f"A Server exception error was thrown: {data.error}")
                                                   )
                                     )
        self.hub_connection.on_open(lambda: (self.hub_connection.send('AddToGroup', [str(self.room_id)]),
                                             self.hub_connection.send('AddToGroup', [str(self.device_unique_id)]),
                                             print(f">>> room_controller - {self.device_unique_id} - signalR "
                                                   f"handshake received. Ready to send/receive messages.")
                                             , self.signalr_connected(True)
                                             )
                                    )
        self.hub_connection.on_reconnect(lambda: (print(f">>> room_controller - Trying to re-connect to"
                                                        f" {API_SIGNALR}")
                                                  ))

        self.hub_connection.on('ping', (lambda: (print(f">>> room_controller - {self.device_unique_id} - PING "
                                                       f"command received"), self.ping_response())))

        self.hub_connection.on('restart', (lambda: (print(f">>> room_controller - {self.device_unique_id} - RESTART "
                                                          f"command received"), self.restart_rc())))

        self.hub_connection.on('shutdown', (lambda: (print(f">>> room_controller - {self.device_unique_id} - SHUTDOWN "
                                                           f"command received"), self.shutdown_rc())))

        self.hub_connection.on('game_status'
                               , (lambda data: (self.set_game_status(data)
                                                , print(f">>> room_controller - {self.device_unique_id} - "
                                                        f"GameStatus command received. Status = {data}")
                                                )))

        print(f">>> room_controller - {self.device_unique_id} - starting signalR")
        self.hub_connection.start()
        print(f">>> room_controller - {self.device_unique_id} - waiting for signalR handshake ...")

        while self.signalr_status is not True:
            try:
                if self.signalr_status is True:
                    break
                else:
                    # print(self.server_url)
                    # print(f'>>> room_controller - SignalR Status: {self.signalr_status}')
                    time.sleep(0)

            except socket.error as error:
                print(f'>>> room_controller - {self.device_unique_id} - SignalR connection ERROR ... {error}')
                self.signalr_status = False
                self.hub_connection.stop()
                time.sleep(5)
                self.hub_connection.start()
                time.sleep(5)

        else:
            print(f">>> room_controller - {self.device_unique_id} - SignalR Connected")

    def signalr_connected(self, status):
        if status is True:
            self.signalr_status = True
        else:
            self.signalr_status = False

    def set_game_status(self, game_status):
        # command received by hub to refresh values from all device threads to update location workspace
        global GLOBAL_GAME_STATUS
        try:
            GLOBAL_GAME_STATUS = int(game_status[0])
        except Exception as error:
            print(f">>> heartbeat - {self.device_unique_id} - GLOBAL_GAME_STATUS Error: {error}")

    def set_device_unique_id(self, unique_device_id):
        # command received by hub to refresh values from all device threads to update location workspace
        global GLOBAL_DEVICE_UNIQUE_ID
        try:
            GLOBAL_DEVICE_UNIQUE_ID = GLOBAL_DEVICE_UNIQUE_ID
        except Exception as error:
            print(f">>> heartbeat - {self.device_unique_id} - GLOBAL_DEVICE_UNIQUE_ID Error: {error}")

    def reset_room_controller(self):
        pass

    def ping_response(self):
        self.hub_connection.send('ping_response', [str(self.device_unique_id), "true"])
        print(f">>> heartbeat - {self.device_unique_id} - PING Response Sent")

    # @staticmethod
    def restart_rc(self):
        try:
            if platform.system() == "Windows":
                # win32api.InitiateSystemShutdown()
                print(f">>> heartbeat - {self.device_unique_id} - Windows Room Controller Rebooting")

            elif platform.system() == "Linux" or platform.system() == "Linux2":
                import dbus

                bus = dbus.SystemBus()
                bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
                bus_object.Reboot(True, dbus_interface="org.freedesktop.login1.Manager")
                print(f">>> heartbeat - {self.device_unique_id} - Room Controller Rebooting")
                exit()
            else:
                print(f">>> heartbeat - {self.device_unique_id} - OS Reboot Command not Supported")

        except Exception as error:
            print(f">>> heartbeat - {self.device_unique_id} - ERROR: {error}")
            print(f">>> heartbeat - {self.device_unique_id} - Error Sending Reboot Command")

    # @staticmethod
    def shutdown_rc(self):
        try:
            if platform.system() == "Windows":
                # win32api.InitiateSystemShutdown()
                print(f">>> heartbeat - {self.device_unique_id} - Windows Room Controller Rebooting")

            elif platform.system() == "Linux" or platform.system() == "Linux2":
                import dbus

                bus = dbus.SystemBus()
                bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
                bus_object.PowerOff(True, dbus_interface="org.freedesktop.login1.Manager")
                print(f">>> heartbeat - {self.device_unique_id} - Shutting Down Room Controller")
            else:
                print(f">>> heartbeat - {self.device_unique_id} - OS Reboot Command not Supported")

        except Exception as error:
            print(f">>> heartbeat - {self.device_unique_id} - ERROR: {error}")
            print(f">>> heartbeat - {self.device_unique_id} - Error Sending Reboot Command")


# HeartBeat Thread to monitor system and game status in a separate process
class HeartbeatThread(threading.Thread):
    def __init__(self):
        super(HeartbeatThread, self).__init__()
        print(">>> room_controller - HeartBeat Thread active ....")

        # global attributes
        self.active = None
        self.heartbeat_instance = None

    def run(self):
        self.heartbeat_instance = heartbeat.Heartbeat()
        print(">>> room_controller - Stopped Base Heartbeat Thread ...")
        heartbeat.HEARTBEAT_STOP = False
        return


# HeartBeat Thread to monitor system and game status in a separate process
class WebsocketServerThread(threading.Thread):
    def __init__(self):
        super(WebsocketServerThread, self).__init__()
        print(">>> room_controller - WebSocket Server Thread active ....")

        # global attributes
        self.active = None
        self.WebsocketServer_instance = None

    def run(self):
        print(">>> room_controller - Starting WebSocket Server Thread ...")
        self.WebsocketServer_instance = websocket_server.WebsocketServer()
        print(">>> room_controller - Stopped WebSocket Server Thread ...")
        websocket_server.WEBSOCKETSERVER_STOP = False
        return
