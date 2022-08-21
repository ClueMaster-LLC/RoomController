import os
import json
import requests
from apis import *
from string import Template
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class RoomController:
    def __init__(self):
        super(RoomController, self).__init__()

        print(">>> Console Output - Room Controller")

        # global attributes
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.known_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "known_devices.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        pass

    def execution_environment(self):
        if os.path.isfile(self.known_devices_file):
            with open(self.known_devices_file) as known_devices_file_i:
                json_response_of_known_devices_file = json.load(known_devices_file_i)

            mac_address_of_known_devices = json_response_of_known_devices_file["devices_mac"]
            self.connect_and_stream_data(mac_ids=mac_address_of_known_devices)

        # while True:
        #     try:
        #         # wait for requests from webapp to add new devices
        #         pass
        #
        #     except requests.exceptions.ConnectionError:
        #         # sleep for 1 sec before trying again
        #         continue

    @staticmethod
    def connect_and_stream_data(mac_ids):
        print(">>> Console output - Starting threads...")
        pass
