import os
import time
import datetime
import json
import requests
import connect_and_stream
from requests.structures import CaseInsensitiveDict
from apis import *

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class ConnectedDevices:
    def __init__(self):
        super(ConnectedDevices, self).__init__()

        # global attributes
        self.active = None
        self.connect_and_stream_thread_instance = None
        self.previously_configured_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")

        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.get_devicelist_api = None
        self.resetting_room_controller = False
        self.get_devicelist_request_api = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found",
                                          "No record found in inventory master"]
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        
        # instance methods
        self.configurations()
        self.init_device_list()
        self.execution_environment()

    def configurations(self):
        try:
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            device_unique_id = json_response_of_unique_ids_file["device_id"]
            api_key = json_response_of_unique_ids_file["api_token"]

        except FileNotFoundError:
            print(">>> connected_devices - Unique ids file not found")

        else:
            self.device_unique_id = device_unique_id
            self.api_token = api_key

            self.api_headers = CaseInsensitiveDict()
            self.api_headers["Authorization"] = f"Basic {device_unique_id}:{api_key}"
            self.discover_new_relays_request_api = NEW_RELAYS_DISCOVERY_REQUEST.format(device_id=device_unique_id)
            self.get_devicelist_request_api = GET_NEW_INPUT_RELAY_LIST_REQUEST.format(device_id=device_unique_id)
            self.get_devicelist_api = GET_NEW_INPUT_RELAY_LIST.format(device_id=device_unique_id)

    def init_device_list(self):
        try:
            print(">>> connected_devices - Download new device list form ClueMaster")
            get_devicelist_response = self.get_devicelist()
            print(">>> connected_devices - Update Connected_Devices.JSON file")
            self.save_device_info(get_devicelist_response)

        except requests.exceptions.ConnectionError:
            # sleep for 5 sec before trying again
            print(">>> connected_devices - room_controller.py API Connection Error. Retrying in 5 seconds...")
            time.sleep(5)
            init_device_list()

        except requests.exceptions.HTTPError as request_error:
            if "401 Client Error" in str(request_error):
                self.reset_room_controller()
                # sleep for 5 sec before trying again
                time.sleep(5)
                init_device_list()
            else:
                print(">>> connected_devices - room_controller.py Not a API token invalid Error")
                print(">>> connected_devices - " + str(request_error))

        except requests.exceptions.JSONDecodeError as json_error:
            print(">>> connected_devices - room_controller.py JsonDecodeError")
            print(">>> connected_devices - Error ", str(json_error))

    def get_devicelist(self):
        print(">>> connected_devices - API query to download new list of devices")
        get_devicelist = requests.get(self.get_devicelist_api, headers=self.api_headers).json()
        print(">>> connected_devices - New devices info : ", get_devicelist)
        return get_devicelist

    def reset_room_controller(self):
        pass

    @staticmethod
    def save_device_info(api_json_list):
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        device_info_dict = {"Devices": api_json_list}

        with open(device_info_file, "w") as device_info:
            json.dump(device_info_dict, device_info)

    def execution_environment(self):
        with open(self.previously_configured_devices_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)
            for devices in connected_devices_file_response["Devices"]:
                device_mac_address = devices["MacAddress"]
                print(">>> connected_devices - Load ", str(device_mac_address))
                self.start_thread(mac_address=device_mac_address)

    def start_thread(self, mac_address):
        print(f">>> connected_devices - Starting ConnectAndStream Thread for MacAddress {mac_address}")
        self.connect_and_stream_thread_instance = connect_and_stream.ConnectAndStream(device_mac=mac_address)
        self.connect_and_stream_thread_instance.start()
