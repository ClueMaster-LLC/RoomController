import os
import time
import json
import requests
from apis import *
import auto_startup
import room_controller
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class Authentication:
    def __init__(self):
        super(Authentication, self).__init__()
        print(">>> Console Output - Authentication")

        # global attributes
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.resetting_room_controller = False
        
        # instance methods
        self.configuration()
        self.execution_environment()

    def configuration(self):
        pass

    def execution_environment(self):
        try:
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            device_unique_id = json_response_of_unique_ids_file["device_id"]
            api_bearer_key = json_response_of_unique_ids_file["api_token"]
            device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=device_unique_id)

            api_headers = CaseInsensitiveDict()
            api_headers["Authorization"] = f"Basic {device_unique_id}:{api_bearer_key}"

            while True:
                device_request_api_response = requests.get(device_request_api_url, headers=api_headers)

                if device_request_api_response.status_code != 200:
                    print(">>> Console output - Device Request Response != 200")
                    time.sleep(2)
                    continue

                else:
                    print(">>> Console output - Device Request Response 200")
                    break

            while not requests.get(device_request_api_url, headers=api_headers).text == "No record found":
                print(">>> Console Output - Authenticating Device")
                device_request_api_response = requests.get(device_request_api_url, headers=api_headers)
                request_id = device_request_api_response.json()["DeviceRequestid"]

                print(">>> Console output - Request ", device_request_api_response.json())

                identify_device_api_url = POST_ROOM_CONTROLLER_REQUEST.format(device_id=device_unique_id, request_id=request_id)
                requests.post(identify_device_api_url, headers=api_headers)

                time.sleep(2)
                continue

            room_controller_window = room_controller.RoomController()
            room_controller_window.__init__()

        except requests.exceptions.ConnectionError:
            # if the app faces connection error when making api calls, then pass
            pass

        except json.decoder.JSONDecodeError:
            # if the app faces json decode error when opening json files then pass
            pass

        except requests.exceptions.HTTPError as request_error:
            if "401 Client Error" in str(request_error):
                self.reset_room_controller()
            else:
                print(">> Console output - Not a 401 error Master Except Block")
                print(request_error)

    def reset_room_controller(self):
        if self.resetting_room_controller is False:
            self.resetting_room_controller = True

            # calling autostartup
            self.autostartup_window = auto_startup.AutoStartup()
            self.autostartup_window.__int__()
