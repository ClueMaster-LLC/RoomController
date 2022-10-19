import os
import datetime
import json
import time
import requests
from apis import *
import thread_manager
import add_find_device
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class RoomController:
    def __init__(self):
        super(RoomController, self).__init__()
        print(">>> room_controller - ***********STARTUP COMPLETE***********")

        # global attributes
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.discover_new_relays_request_api = None
        self.general_request_api = None
        self.search_for_devices_id = 12
        self.resetting_room_controller = False
        self.connect_and_stream_thread = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found"]

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
            print(">>> room_controller - Unique ids file not found")

        else:
            self.device_unique_id = device_unique_id
            self.api_token = api_key

            self.api_headers = CaseInsensitiveDict()
            self.api_headers["Authorization"] = f"Basic {device_unique_id}:{api_key}"
            self.discover_new_relays_request_api = NEW_RELAYS_DISCOVERY_REQUEST.format(device_id=device_unique_id)

    def execution_environment(self):
        while True:
            try:
                #print(">>> Console Output " + str(datetime.datetime.utcnow()) + " - Searching for new input relays request ...")
                relays_discovery_request = requests.get(self.discover_new_relays_request_api, headers=self.api_headers)
                relays_discovery_request.raise_for_status()

                if relays_discovery_request.text not in self.api_active_null_responses:
                    request_id = relays_discovery_request.json()["RequestID"]

                    if request_id == self.search_for_devices_id:
                        print(">>> room_controller - Acknowledging request for Input Relay with RequestId ", request_id)
                        self.general_request_api = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                                       request_id=request_id)
                        requests.post(self.general_request_api, headers=self.api_headers)
                        ####AFTER API REQUEST TO START (add, find) process,
                        ####return results to API for display on ClueMaster selection page.
                        ####after user selects the devices to add, they will be saved to the sql database.
                        print(">>> room_controller - Add or Find devices and return")                        
                        ####
                        ####Then CALL new API to REQUEST ALL DEVICES FOR THIS ROOM CONTROLLER
                        ####THIS SHOULD INCLUDE THE NEW ONES ADDED TO THE DATABASE
                        ####WE MIGHT NEED A DELAY OR SOME CHECKS TO ENSURE ENOUGH TIME PASSED
                        ####TO ALLOW API TO REFRESH NEW DATA FROM THE SQL DATABASE
                        print(">>> room_controller - IF ADD DEVICE SUCCESS > GET API for new list of devices")
                        print(">>> room_controller - IF FIND DEVICES > GET API for new list of devices")

                    else:
                        print(">>> room_controller - Request id ", relays_discovery_request.json()["RequestID"])

                time.sleep(1)

            except requests.exceptions.ConnectionError:
                # sleep for 1 sec before trying again
                print(">>> room_controller - room_controller.py Connection Error")
                time.sleep(1)
                continue

            except requests.exceptions.HTTPError as request_error:
                if "401 Client Error" in str(request_error):
                    self.reset_room_controller()
                    break
                else:
                    print(">>> room_controller - room_controller.py Not a API token invalid Error")
                    print(request_error)

            except requests.exceptions.JSONDecodeError as json_error:
                print(">>> room_controller - room_controller.py JsonDecodeError")
                print(">>> room_controller - Error ", json_error)
                pass

            except KeyboardInterrupt:
                print(">>> room_controller - room_controller.py Keyboard Interrupt")
                break

    @staticmethod
    def connect_and_stream_data():
        print(">>> room_controller - Starting threads...")
        pass

    def reset_room_controller(self):
        pass
