import os
import time
import json
import requests

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class ConnectedDevices:
    def __init__(self):
        super(ConnectedDevices, self).__init__()

        # global attributes
        self.previously_connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        self.previously_connected_devices_file_exists = None

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        if os.path.isfile(self.previously_connected_devices_file):
            self.previously_connected_devices_file_exists = True
        else:
            pass

    def execution_environment(self):
        pass
