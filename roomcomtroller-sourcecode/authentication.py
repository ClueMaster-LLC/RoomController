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
        self.api_headers = None
        self.device_request_api_url = None
        self.api_bearer_key = None
        self.device_unique_id = None
        self.null_responses = ["No room controller found", "No request found", ""]

        # instance methods
        self.configuration()
        self.execution_environment()

    def configuration(self):
        with open(self.unique_ids_file) as unique_ids_file:
            json_response_of_unique_ids_file = json.load(unique_ids_file)

        self.device_unique_id = json_response_of_unique_ids_file["device_id"]
        self.api_bearer_key = json_response_of_unique_ids_file["api_token"]
        self.device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

        self.api_headers = CaseInsensitiveDict()
        self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"

    def execution_environment(self):
        try:
            while True:
                device_request_api_response = requests.get(self.device_request_api_url, headers=self.api_headers)
                if device_request_api_response.text in self.null_responses:
                    print(">>> Console output - No Registration Requests Found")
                    time.sleep(1)
                    continue

                else:
                    print(">>> Console output - Room Controller Registration Requests Found")
                    break

            while requests.get(self.device_request_api_url, headers=self.api_headers).text not in self.null_responses:
                # getting requests and their ids
                device_request_api_response = requests.get(self.device_request_api_url, headers=self.api_headers)
                request_id = device_request_api_response.json()["DeviceRequestid"]

                # acknowledging requests
                identify_device_api_url = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                              request_id=request_id)
                requests.post(identify_device_api_url, headers=self.api_headers)
                print(">>> Console Output - Acknowledging Requestid ", request_id)

            # forwarding application flow to room controller master environment
            room_controller_window = room_controller.RoomController()

        except requests.exceptions.ConnectionError:
            # if the app faces connection error when making api calls, then pass
            print(">>> Console Output - authentication.py Connection Error")
            pass

        except KeyboardInterrupt:
            print(">>> Console Output - authentication.py Keyboard Interrupt")

        except json.decoder.JSONDecodeError as json_error:
            print(">>> Console Output - room_controller.py JsonDecodeError")
            print(">>> Console Output - Error ", json_error)
            i_request = requests.get(self.device_request_api_url, headers=self.api_headers).text
            print(">>> Current General Request API Response - ", i_request)
            pass

        except requests.exceptions.JSONDecodeError as json_error:
            print(">>> Console Output - room_controller.py JsonDecodeError")
            print(">>> Console Output - Error ", json_error)
            pass

        except requests.exceptions.HTTPError as request_error:
            if "401 Client Error" in str(request_error):
                self.reset_room_controller()
            else:
                print(">>> Console output - authentication.py Not a 401 error Master Except Block")
                print(request_error)

    def reset_room_controller(self):
        if self.resetting_room_controller is False:
            self.resetting_room_controller = True

            # calling autostartup
            self.autostartup_window = auto_startup.AutoStartup()
