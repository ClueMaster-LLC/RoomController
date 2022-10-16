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
##        self.execution_environment()

    def configurations(self):
        pass

    def run(self):
        print("hello")

    @staticmethod
    def execution_environment():
        while True:
            print(">>> Console Output - Connect to previously configured devices ... ")
            time.sleep(2)

    def read_device_info():
        try:
            connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
            with open(connected_devices_file, "r") as device_info:
                device_info_response = json.load(device_info)

            for i in device_info_response.items():
                values = i[1]
##                if values["MacAddress"] == "0008DC21DDFD":
##                    print("Matched..")
                return values["MacAddress"]
                
        except Exception:
            print(">>> Console Output - device_info file does not exist or there is improperly formatted data")

def start_thread():
    if __name__ == "__main__":
        connected_devices_stream_instance = ConnectedDevices()
        connected_devices_stream_instance.start()

start_thread()
