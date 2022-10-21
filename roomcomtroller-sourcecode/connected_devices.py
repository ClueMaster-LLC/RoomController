import os
import time
import json
import requests
import connect_and_stream

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
        self.connect_and_stream_thread_instance = None
        self.previously_configured_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        pass

    def execution_environment(self):
        with open(self.previously_configured_devices_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)
            for devices in connected_devices_file_response["Devices"]:
                device_mac_address = devices["MacAddress"]
                print(">>> connected_devices - Load ", str(device_mac_address))
                self.start_thread(mac_address=device_mac_address)

    def start_thread(self, mac_address):
        print(f">>> connected_devices - Starting ConnectAndStream Thread for MacAddress {mac_address}")
        self.connect_and_stream_thread_instance = connect_and_stream.ConnectAndStream(device_mac=mac_address)
        self.connect_and_stream_thread_instance.start()
