import os
import re
import json
import uuid
import time
import socket
import requests
import authentication
import room_controller
from apis import *
from string import Template
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class AutoStartup:

    def __int__(self):
        super(AutoStartup, self).__init__()
        print(">>> Console Output - AutoStartup")

        # global attributes
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.device_status = True

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        pass

    def execution_environment(self):
        # the main functionalities of the splash screen lies here -----
        time.sleep(2)

        if os.path.isdir(APPLICATION_DATA_DIRECTORY) is False:
            os.makedirs(APPLICATION_DATA_DIRECTORY)
        else:
            pass

        if os.path.isfile(self.unique_ids_file):
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            device_unique_id = json_response_of_unique_ids_file["device_id"]
            api_bearer_key = json_response_of_unique_ids_file["api_token"]
            get_rc_request_api = ROOM_CONTROLLER_REQUEST_API.format(device_id=device_unique_id)

            # request api call headers
            api_header = CaseInsensitiveDict()
            api_header["Authorization"] = f"Basic {device_unique_id}:{api_bearer_key}"

            while True:
                try:
                    if requests.get(get_rc_request_api, headers=api_header).status_code != 200:
                        print(">>> Console output - API token invalid. Creating New Token")
                        new_api_bearer_key = self.generate_secure_api_token(device_id=device_unique_id)
                        json_response_of_unique_ids_file["api_token"] = new_api_bearer_key
                        self.device_status = False

                    else:
                        self.device_status = True

                    # committing newly generated token to unique_ids_file
                    ipv4_address = self.fetch_device_ipv4_address()
                    json_response_of_unique_ids_file["IPv4 Address"] = ipv4_address

                    with open(self.unique_ids_file, "w") as unique_code_json_file:
                        json.dump(json_response_of_unique_ids_file, unique_code_json_file)

                    self.validate_device_status()

                except requests.exceptions.ConnectionError:
                    time.sleep(2)
                    continue

                else:
                    break

        else:
            device_macaddress = '-'.join(re.findall('....', '%012x' % uuid.getnode())).upper()
            api_bearer_key = self.generate_secure_api_token(device_id=device_macaddress)
            device_ipaddress = self.fetch_device_ipv4_address()

            unique_ids_dictionary = {"device_id": device_macaddress, "api_token": api_bearer_key,
                                     "ip_address": device_ipaddress}

            with open(self.unique_ids_file, "w") as unique_ids_file:
                json.dump(unique_ids_dictionary, unique_ids_file)

            self.device_status = False
            self.validate_device_status()

    @staticmethod
    def generate_secure_api_token(device_id):
        while True:
            try:
                authentication_api_url = GENERATE_API_TOKEN_API
                device_id = device_id

                api_headers = CaseInsensitiveDict()
                api_headers["Content-Type"] = "application/json"

                initial_template = Template("""{"DeviceKey": "${device_key}", "Username": "ClueMasterAPI", 
                "Password": "8BGIJh27uBtqBTb2%t*zho!z0nS62tq2pGN%24&5PS3D"}""")
                bearer_data = initial_template.substitute(device_key=device_id)

                response = requests.post(url=authentication_api_url, headers=api_headers, data=bearer_data).json()
                print(">>> Console output - API Auth status - ", response["status"])
                print(">>> Console Output - New Token ", response["apiKey"])
                return response["apiKey"]

            except requests.exceptions.ConnectionError:
                time.sleep(3)
                pass

    @staticmethod
    def fetch_device_ipv4_address():
        i_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            i_socket.connect(('10.255.255.255', 1))
            ip_address = i_socket.getsockname()[0]
        except Exception:
            ip_address = "127.0.0.1"
        finally:
            i_socket.close()

        return ip_address

    def validate_device_status(self):
        if self.device_status is False:
            authentication_window = authentication.Authentication()
            authentication_window.__init__()
        else:
            room_controller_window = room_controller.RoomController()
            room_controller_window.__init__()
