import os
import json
import time
import platform

from apis import *
from requests.structures import CaseInsensitiveDict

## This import will be for signalR code##
import logging
from signalrcore.hub_connection_builder import HubConnectionBuilder

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# global variables
global_active_mac_ids = []


# master class
class Heartbeat:
    def __init__(self):
        super(Heartbeat, self).__init__()

        # local class attributes
        self.get_devicelist_request_api = None
        self.discover_new_relays_request_api = None
        self.hub_connection = None
        self.handler = None
        self.server_url = None
        self.active_mac_ids = []
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.get_devicelist_api = None
        self.general_request_api = None
        self.resetting_heartbeat = False
        # self.connect_and_stream_thread = None
        # self.add_find_device_thread = None
        # self.get_devicelist_request_api = None
        self.signalr_status = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found",
                                          "No record found in inventory master"]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")

        # instance methods
        self.configurations()
        self.signalr_hub()
        print(">>> heartbeat - **********  STARTUP COMPLETE  **********")
        self.execution_environment()
        print(">>> heartbeat - **********  HEARTBEAT THREAD SHUTTING DOWN  **********")

    def configurations(self):
        try:
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

            device_unique_id = json_response_of_unique_ids_file["device_id"]
            api_key = json_response_of_unique_ids_file["api_token"]

            self.device_unique_id = device_unique_id
            self.api_token = api_key

            self.api_headers = CaseInsensitiveDict()
            self.api_headers["Authorization"] = f"Basic {device_unique_id}:{api_key}"
            self.discover_new_relays_request_api = NEW_RELAYS_DISCOVERY_REQUEST.format(device_id=device_unique_id)
            self.get_devicelist_request_api = GET_NEW_INPUT_RELAY_LIST_REQUEST.format(device_id=device_unique_id)
            self.get_devicelist_api = GET_NEW_INPUT_RELAY_LIST.format(device_id=device_unique_id)

            # load all the devices on startup into memory array
            # self.init_previous_devices()
            # self.handling_devices_info()

        except Exception as ErrorFileNotFound:
            print(f'>>> automation - Error: {ErrorFileNotFound}')

    def signalr_hub(self):
        self.server_url = API_SIGNALR
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.ERROR)
        self.hub_connection = HubConnectionBuilder() \
            .with_url(self.server_url, options={
                "verify_ssl": True,
                "skip_negotiation": False,
                "http_client_options": {"headers": self.api_headers, "timeout": 5.0},
                "ws_client_options": {"headers": self.api_headers, "timeout": 5.0},
            }) \
            .configure_logging(logging.ERROR, socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect({
                "type": "raw",
                "keep_alive_interval": 5,
                "reconnect_interval": 5,
                "max_attempts": 99999999
            }).build()

        self.hub_connection.on_close(lambda: print(">>> heartbeat - SignalR Connection Closed"))
        self.hub_connection.on_error(lambda data: (print(f">>> connect_and_stream - An exception was thrown: "
                                                         f"{data.error}"), self.signalr_connected(False)))
        self.hub_connection.on_open(lambda: (print(
            ">>> heartbeat - signalR handshake received. Ready to send/receive messages."),
                                             self.signalr_connected(True)))
        self.hub_connection.on_reconnect(lambda: print(">>> heartbeat - Trying to re-connect to "
                                                       "comhub.cluemaster.io"))

        self.hub_connection.start()

        while self.signalr_status is not True:
            for i in range(15, -1, -1):
                if self.signalr_status is True:
                    break
                if i == 0:
                    print(f'>>> heartbeat - timeout exceeded. SignalR not connected.')
                    break
                print(f'>>> heartbeat - waiting for signalR handshake ... {i}')
                time.sleep(1)
            break
        else:
            print(">>> heartbeat - signalr connected")

    def signalr_connected(self, status):
        if status is True:
            self.signalr_status = True
        elif not status:
            self.signalr_status = False

    def execution_environment(self):
        while True:
            # print(">>> heartbeat - waiting for heartbeat action")
            time.sleep(5)
            # run heartbeat logic here

    @staticmethod
    def reboot_rc():
        try:
            if platform.system() == "Windows":
                # win32api.InitiateSystemShutdown()
                print(">>> add_find_device - Windows Room Controller Rebooting")
                pass
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                os.system('systemctl reboot -i')
            print(">>> add_find_device - Room Controller Rebooting")

        except Exception as error:
            print(f">>> add_find_device - ERROR: {error}")
            print(">>> add_find_device - Error Sending Reboot Command")

# def main():
#     if __name__ == "__main__":
#         Heartbeat = Heartbeat()
#         Heartbeat.start()
#
#
# main()
