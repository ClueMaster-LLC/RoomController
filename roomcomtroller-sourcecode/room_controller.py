import os
import json
import time
import requests
import threading
from apis import *
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.getcwd(), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class RoomController:
    def __init__(self):
        super(RoomController, self).__init__()
        print(">>> Console Output - Room Controller")

        # global attributes
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.discover_new_relays_request_api = None
        self.general_request_api = None
        self.search_for_devices_id = 12
        self.null_responses = ["No room controller found", "No request found", "No record found"]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.known_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "known_devices.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        try:
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            device_unique_id = json_response_of_unique_ids_file["device_id"]
            api_key = json_response_of_unique_ids_file["api_token"]

        except FileNotFoundError:
            print(">>> Console output - Unique ids file not found")

        else:
            self.device_unique_id = device_unique_id
            self.api_token = api_key

            self.api_headers = CaseInsensitiveDict()
            self.api_headers["Authorization"] = f"Basic {device_unique_id}:{api_key}"
            self.discover_new_relays_request_api = NEW_RELAYS_DISCOVERY_REQUEST.format(device_id=device_unique_id)

    def execution_environment(self):
        if os.path.isfile(self.known_devices_file):
            with open(self.known_devices_file) as known_devices_file_i:
                json_response_of_known_devices_file = json.load(known_devices_file_i)

            mac_address_of_known_devices = json_response_of_known_devices_file["devices_mac"]
            self.connect_and_stream_data(mac_ids=mac_address_of_known_devices)

        while True:
            try:
                print(">>> Console Output - Searching for new input relays request ...")

                relays_discovery_request = requests.get(self.discover_new_relays_request_api, headers=self.api_headers)

                if relays_discovery_request.text not in self.null_responses:
                    request_id = relays_discovery_request.json()["RequestID"]

                    if request_id == self.search_for_devices_id:
                        print(">>> Console Output - Acknowledging request for Input Relay with RequestId ", request_id)
                        self.general_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id, request_id=request_id)
                        requests.post(self.general_request_api, headers=self.api_headers)
                    else:
                        print(">>> Console Output - Request id ", relays_discovery_request.json()["RequestID"])

                time.sleep(1)

            except requests.exceptions.ConnectionError:
                # sleep for 1 sec before trying again
                print(">>> Console Output - room_controller.py Connection Error")
                time.sleep(1)
                continue

            except requests.exceptions.JSONDecodeError as json_error:
                print(">>> Console Output - room_controller.py JsonDecodeError")
                print(">>> Console Output - Error ", json_error)
                pass

            except KeyboardInterrupt:
                print(">>> Console Output - room_controller.py Keyboard Interrupt")
                break

    @staticmethod
    def connect_and_stream_data(mac_ids):
        print(">>> Console output - Starting threads...")
        pass
