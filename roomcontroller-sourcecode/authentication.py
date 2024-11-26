import os
import time
import datetime
import logging
import json
import requests
from apis import *
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
        print(">>> authentication - Authentication Process Starting")

        # global attributes
        self.api_headers = None
        self.device_request_api_url = None
        self.api_bearer_key = None
        self.device_unique_id = None
        self.api_active_null_responses = ["No room controller found", "No request found", ""]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")

        # level    = logging.INFO
        # format   = '  %(message)s'
        # handlers = [logging.FileHandler('filename.log'), logging.StreamHandler()]
        #
        # logging.basicConfig(level = level, format = format, handlers = handlers)
        # logging.info('>>> authentication - Authentication Process Starting')

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
        print(">>> authentication - MAC ADDRESS: " + str(self.device_unique_id))

    def execution_environment(self):
        try:
            while True:
                device_request_api_response = requests.get(self.device_request_api_url, headers=self.api_headers)
                if device_request_api_response.text in self.api_active_null_responses:
                    print(">>> authentication " + str(datetime.datetime.utcnow()) +
                          " - No Registration Requests Found For: " + self.device_unique_id)
                    # logging.info(">>> authentication " + str(datetime.datetime.utcnow()) +
                    #              " - No Registration Requests Found For: " + self.device_unique_id)
                    time.sleep(5)
                    continue

                else:
                    print(">>> authentication " + str(datetime.datetime.utcnow()) + "- Room Controller Registration "
                                                                                    "Requests Found")
                    break

            while requests.get(self.device_request_api_url,
                               headers=self.api_headers).text not in self.api_active_null_responses:

                # getting requests and their ids
                device_request_api_response = requests.get(self.device_request_api_url, headers=self.api_headers)
                request_id = device_request_api_response.json()["DeviceRequestid"]

                # acknowledging requests
                identify_device_api_url = POST_ROOM_CONTROLLER_REQUEST.format(device_id=self.device_unique_id,
                                                                              request_id=request_id)
                requests.post(identify_device_api_url, headers=self.api_headers)
                print(">>> authentication - Acknowledging Requestid ", request_id)

            # forwarding application flow to room controller master environment
            room_controller_window = room_controller.RoomController()

        except requests.exceptions.ConnectionError:
            # if the app faces connection error when making api calls, then pass
            print(">>> authentication - authentication.py Connection Error")
            pass

        except requests.exceptions.HTTPError as request_error:
            if "401 Client Error" in str(request_error):
                self.reset_room_controller()

            else:
                print(">>> authentication - Not a API token invalid Error")
                print(request_error)

        except KeyboardInterrupt:
            print(">>> authentication - authentication.py Keyboard Interrupt")
            return

        except json.decoder.JSONDecodeError as json_error:
            print(">>> authentication - JsonDecodeError")
            print(">>> authentication - Error ", json_error)
            i_request = requests.get(self.device_request_api_url, headers=self.api_headers).text
            print(">>> authentication - API Response Error - ", i_request)
            time.sleep(5)
            # forwarding application flow to room controller master environment to run offline
            room_controller_window = room_controller.RoomController()
            pass

        except requests.exceptions.JSONDecodeError as json_error:
            print(">>> authentication - JsonDecodeError")
            print(">>> authentication - Error ", json_error)
            pass

    def reset_room_controller(self):
        pass
