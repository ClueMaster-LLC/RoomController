import os
import platform
import json
import time
import logging
import socket
import psutil
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
        print(">>> auto_startup - AutoStartup")

        # global attributes
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found"]
        self.device_status = True

        level    = logging.INFO
        format   = '  %(message)s'
        handlers = [logging.FileHandler('filename.log'), logging.StreamHandler()]

        logging.basicConfig(level = level, format = format, handlers = handlers)
        logging.info('>>> auto_startup - AutoStartup Process Starting')

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        pass

    def execution_environment(self):
        # the main functionalities of the splash screen lies here -----

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
                    room_controller_response = requests.get(get_rc_request_api, headers=api_header)
                    if room_controller_response.status_code in [401, 500, 501]:

                        print(">>> auto_startup - API token invalid. Creating New Token")
                        new_api_bearer_key = self.generate_secure_api_token(device_id=device_unique_id)
                        json_response_of_unique_ids_file["api_token"] = new_api_bearer_key
                        self.device_status = False

                    else:
                        self.device_status = True

                    if room_controller_response.text not in self.api_active_null_responses:
                        try:
                            temp_response = room_controller_response.json()
                            if temp_response["DeviceRequestid"] <= 7:
                                self.device_status = False
                            else:
                                pass

                        except json.decoder.JSONDecodeError:
                            self.device_status = False

                    else:
                        if room_controller_response.text == "":
                            self.device_status = False
                        else:
                            self.device_status = True

                    # committing newly generated token to unique_ids_file
                    ipv4_address = self.fetch_device_ipv4_address()
                    json_response_of_unique_ids_file["ip_address"] = ipv4_address

                    with open(self.unique_ids_file, "w") as unique_code_json_file:
                        json.dump(json_response_of_unique_ids_file, unique_code_json_file)

                    print(">>> auto_startup - MAC ADDRESS ", str(device_unique_id))
                    self.validate_device_status()

                except requests.exceptions.ConnectionError:
                    print(">>> auto_startup - Connection Error")
                    time.sleep(1)
                    continue

                except json.decoder.JSONDecodeError as json_error:
                    print(">>> auto_startup - JsonDecodeError")
                    print(">>> auto_startup - Error ", json_error)
                    i_request = requests.get(get_rc_request_api, headers=api_header).text
                    print(">>> auto_startup - Current General Request API Response - ", i_request)
                    time.sleep(5)
                    pass

                else:
                    break

        else:
            device_ipaddress = self.fetch_device_ipv4_address()
            device_macaddress = self.fetch_active_network_interface_mac_address(ip_address=device_ipaddress)
            api_bearer_key = self.generate_secure_api_token(device_id=device_macaddress)

            unique_ids_dictionary = {"device_id": device_macaddress, "api_token": api_bearer_key,
                                     "ip_address": device_ipaddress}

            with open(self.unique_ids_file, "w") as unique_ids_file:
                json.dump(unique_ids_dictionary, unique_ids_file)

            print(">>> auto_startup - MAC ADDRESS ", str(device_macaddress))
            self.device_status = False
            self.validate_device_status()

    @staticmethod
    def fetch_active_network_interface_mac_address(ip_address):

        if platform.system() == "Windows":
            print(">>> auto_startup - Platform in use : ", platform.system())
            for i in psutil.net_if_addrs().items():
                interface_ip_address = i[1][1][1]
                print(">>> auto_startup - Other IPs found " + interface_ip_address)

                if interface_ip_address == ip_address:
                    i_mac_address = i[1][0][1].split("-")

                    first_pair = "".join(i_mac_address[0:2]).upper()
                    second_pair = "".join(i_mac_address[2:4]).upper()
                    third_pair = "".join(i_mac_address[4:8]).upper()
                    active_mac_address = first_pair + "-" + second_pair + "-" + third_pair

                    return active_mac_address

        elif platform.system() == "Linux" or platform.system() == "Linux2":
            print(">>> auto_startup - Platform in use :", platform.system())
            for i in psutil.net_if_addrs().items():
                interface_ip_address = i[1][0][1]
                print(">>> auto_startup - Other IPs found " + interface_ip_address)

                if interface_ip_address == ip_address:
                    i_mac_address = i[1][2][1].split(":")

                    first_pair = "".join(i_mac_address[0:2]).upper()
                    second_pair = "".join(i_mac_address[2:4]).upper()
                    third_pair = "".join(i_mac_address[4:8]).upper()
                    active_mac_address = first_pair + "-" + second_pair + "-" + third_pair

                    return active_mac_address
        else:
            print(platform.system() + "OS not supported")

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
                print(">>> auto_startup - API Auth status - ", response["status"])
                print(">>> auto_startup - New Token ", response["apiKey"])
                return response["apiKey"]

            except requests.exceptions.ConnectionError:
                print(">>> auto_startup - Connection Error")
                time.sleep(1)
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
            print(">>> auto_startup - Gateway IP Address: " + ip_address)
        return ip_address

    def validate_device_status(self):
        print(">>> auto_startup - Validating Device Status")
        if self.device_status is False:
            authentication_window = authentication.Authentication()
        else:
            room_controller_window = room_controller.RoomController()
