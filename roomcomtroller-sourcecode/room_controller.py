import os
import datetime
import json
import time
import requests
from apis import *
import thread_manager
import connect_and_stream
import add_find_device
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

#global variables
global_active_mac_ids = []

# master class
class RoomController:
    def __init__(self):
        super(RoomController, self).__init__()
        print(">>> room_controller - **********  STARTUP COMPLETE  **********")

        # global attributes
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.discover_new_relays_request_api = None
        self.get_devicelist_api = None
        self.general_request_api = None
        self.search_for_devices_id = 12
        self.update_device_list_id = 13
        self.resetting_room_controller = False
        self.connect_and_stream_thread = None
        self.add_find_device_thread = None
        self.get_devicelist_request_api = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found",
                                          "No record found in inventory master"]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def global_active_mac_id(self):
        return global_active_mac_ids

    def configurations(self):
        try:
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            device_unique_id = json_response_of_unique_ids_file["device_id"]
            api_key = json_response_of_unique_ids_file["api_token"]

            #load all the devices on startup into memory array
            self.active_devices()
            self.handling_devices_info()

        except FileNotFoundError:
            print(">>> room_controller - Unique ids file not found")

        else:
            self.device_unique_id = device_unique_id
            self.api_token = api_key

            self.api_headers = CaseInsensitiveDict()
            self.api_headers["Authorization"] = f"Basic {device_unique_id}:{api_key}"
            self.discover_new_relays_request_api = NEW_RELAYS_DISCOVERY_REQUEST.format(device_id=device_unique_id)
            self.get_devicelist_request_api = GET_NEW_INPUT_RELAY_LIST_REQUEST.format(device_id=device_unique_id)
            self.get_devicelist_api = GET_NEW_INPUT_RELAY_LIST.format(device_id=device_unique_id)

    def execution_environment(self):
        while True:
            try:
                # print(">>> Console Output " + str(datetime.datetime.utcnow()) + " - Searching for new input relays request ...")
                relays_discovery_request = requests.get(self.discover_new_relays_request_api, headers=self.api_headers)
                # print(">>> room_controller - " + str(datetime.datetime.utcnow()) + "Waiting for code 12,13 : " + relays_discovery_request.text)
                relays_discovery_request.raise_for_status()

                if relays_discovery_request.text not in self.api_active_null_responses:
                    request_id = relays_discovery_request.json()["RequestID"]

                    if request_id == self.search_for_devices_id:
                        print(">>> room_controller - Acknowledging request for Input Relay with RequestId ", request_id)
                        self.general_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                       request_id=request_id)
                        requests.post(self.general_request_api, headers=self.api_headers)

                        # staring add_find_device thread
                        self.start_add_find_device_thread(response=relays_discovery_request.json())
                    else:
                        print(">>> room_controller - Unexpected Request id:", str(request_id), "returned.")
                # print("Sleep 3")
                # time.sleep(3)

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

                        self.general_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                       request_id=request_id)
                        requests.post(self.general_request_api, headers=self.api_headers)
                        # print(requests.post(self.general_request_api, headers=self.api_headers))

                        # download latest list of devices from ClueMaster to refresh list if request_id=13
                        print(">>> room_controller - Download new device list form ClueMaster")
                        get_devicelist_response = self.get_devicelist()
                        print(">>> room_controller - Update Connected_Devices.JSON file")
                        self.save_device_info(get_devicelist_response)

                        # handling new devices added
                        new_devices = self.handling_devices_info()
                        if new_devices != None:
                            for device in new_devices:
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
                    break
                else:
                    print(">>> room_controller - room_controller.py Not a API token invalid Error")
                    print(">>> room_controller - " + str(request_error))

            except requests.exceptions.JSONDecodeError as json_error:
                print(">>> room_controller - room_controller.py JsonDecodeError")
                print(">>> room_controller - Error ", str(json_error))
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

    def get_devicelist(self):
        print(">>> room_controller - API query to download new list of devices")
        get_devicelist = requests.get(self.get_devicelist_api, headers=self.api_headers).json()
        print(">>> room_controller - New devices info : ", get_devicelist)
        return get_devicelist

    #@staticmethod
    def save_device_info(self, api_json_list):
        #device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        device_info_dict = {"Devices": api_json_list}

        with open(self.connected_devices_file, "w") as device_info:
            json.dump(device_info_dict, device_info)

    def handling_devices_info(self):
        # only handles creating of new individual threads and not explicitly termination of threads...
        # termination of threading will be handled in ConnectAndStream thread class --- pending

        devices_mac_ids = []
        new_devices = []
        #all_mac_ids = []

##        with open(self.connected_devices_file) as connected_devices_file:
##            connected_devices_file_response = json.load(connected_devices_file)
##
##            for devices in connected_devices_file_response["Devices"]:
##                all_mac_ids.append(devices["MacAddress"])
##                devices_mac_ids.append("device_" + devices["MacAddress"] + "_streaming")
##
##        print(">>> room_controller - Updating Environment Variables: " + str(all_mac_ids))
##        os.environ["Registered_Devices"] = ",".join(all_mac_ids)
##
##        with open(self.roomcontroller_configs_file) as room_controller_configs_file:
##            room_controller_configs_file_response = json.load(room_controller_configs_file)
##
##            for mac_ids in devices_mac_ids:
##                if mac_ids in room_controller_configs_file_response.keys():
##                    pass
##                else:
##                    new_devices.append(mac_ids.split("_")[1])

        with open(self.connected_devices_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)

            for devices in connected_devices_file_response["Devices"]:
                devices_mac_ids.append(devices["MacAddress"])

        print(">>> room_controller - Updating GV - Previously Connected Devices : " + str(devices_mac_ids))

        for device in devices_mac_ids:
            if device in global_active_mac_ids:
                pass
            else:
                new_devices.append(devices_mac_ids)
                print(">>> room_controller - Updating GV - New Connected Devices : " + str(new_devices))
                os.environ['Registered_Devices'] = str(new_devices)
                print(">>> room_controller - Updating ENV VAR - ", os.environ.get('Registered_Devices'))

        return new_devices

    def active_devices(self):
        with open(self.connected_devices_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)

            for devices in connected_devices_file_response["Devices"]:
                global_active_mac_ids.append(devices["MacAddress"])

        print(">>> room_controller - Loading Previously Connected Devices into Global Variable: " + str(global_active_mac_ids))
        os.environ['Registered_Devices'] = str(global_active_mac_ids)
        #print(global_active_mac_ids)


    def connect_and_stream_data(self, device_mac_id):
        print(">>> room_controller - Starting ConnectAndStream thread for device - ", device_mac_id)
        self.connect_and_stream_thread = connect_and_stream.ConnectAndStream(device_mac=device_mac_id)
        self.connect_and_stream_thread.start()

    def reset_room_controller(self):
        pass
