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
        self.active = None

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        pass

    def execution_environment(self):
        while True:
            print(">>> Console Output - Connect to previously configured devices ... ")
            time.sleep(2)
