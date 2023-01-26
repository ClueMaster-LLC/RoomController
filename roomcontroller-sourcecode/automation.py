import os
import json
import time
import platform
# import requests
# import connect_and_stream
# import add_find_device
# import connected_devices

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
class Automation:
    def __init__(self):
        super(Automation, self).__init__()

        # local class attributes
        self.hub_connection = None
        self.handler = None
        self.server_url = None
        self.active_mac_ids = []
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.discover_new_relays_request_api = None
        self.get_devicelist_api = None
        self.general_request_api = None
        self.search_for_devices_id = 12
        self.update_device_list_id = 13
        self.resetting_automation = False
        self.connect_and_stream_thread = None
        self.add_find_device_thread = None
        self.get_devicelist_request_api = None
        self.signalr_status = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found",
                                          "No record found in inventory master"]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")

        # instance methods
        self.configurations()
        self.signalr_hub()
        print(">>> automation - **********  STARTUP COMPLETE  **********")
        self.execution_environment()
        print(">>> automation - **********  ROOM CONTROLLER SHUTTING DOWN  **********")

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

        self.hub_connection.on_close(lambda: print(">>> automation - SignalR Connection Closed"))
        self.hub_connection.on_error(lambda data: (print(f">>> connect_and_stream - An exception was thrown: "
                                                         f"{data.error}"), self.signalr_connected(False)))
        self.hub_connection.on_open(lambda: (print(
            ">>> automation - signalR handshake received. Ready to send/receive messages."),
                                             self.signalr_connected(True)))
        self.hub_connection.on_reconnect(lambda: print(">>> automation - Trying to re-connect to "
                                                       "comhub.cluemaster.io"))

        self.hub_connection.on(str(self.device_unique_id), print)

        # use lambda to process commands for the RC
        self.hub_connection.on('rc_command', print)

        self.hub_connection.start()

        while self.signalr_status is not True:
            for i in range(15, -1, -1):
                if self.signalr_status is True:
                    break
                if i == 0:
                    print(f'>>> automation - timeout exceeded. SignalR not connected.')
                    break
                print(f'>>> automation - waiting for signalR handshake ... {i}')
                time.sleep(1)
            break
        else:
            print(">>> automation - signalr connected")

    def signalr_connected(self, status):
        if status is True:
            self.signalr_status = True
        elif not status:
            self.signalr_status = False

    def execution_environment(self):
        while True:
            # print(">>> automation - waiting for automation action")
            time.sleep(5)
            # run automations here

    # def start_add_find_device_thread(self, response):
    #     if response["IpAddress"] != '':
    #         ip_address = response["IpAddress"]
    #         mac_address = response["macaddress"]
    #         server_port = response["server_port"]
    #
    #         self.add_find_device_thread = add_find_device.AddFindDevices(method='add', ip=ip_address,
    #                                                                      server_port=server_port,
    #                                                                      mac_address=mac_address)
    #         self.add_find_device_thread.start()
    #     else:
    #         self.add_find_device_thread = add_find_device.AddFindDevices(method='find')
    #         self.add_find_device_thread.start()

    # def get_devicelist(self):
    #     print(">>> automation - API query to download new list of devices")
    #     get_devicelist = requests.get(self.get_devicelist_api, headers=self.api_headers).json()
    #     print(">>> automation - New devices info : ", get_devicelist)
    #     return get_devicelist

    # @staticmethod
    # def save_device_info(self, api_json_list):
    #     # device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
    #     device_info_dict = {"Devices": api_json_list}
    #
    #     with open(self.connected_devices_file, "w") as device_info:
    #         json.dump(device_info_dict, device_info)

    # def handling_devices_info(self):
    #     devices_mac_ids = []
    #     new_devices = []
    #
    #     with open(self.connected_devices_file) as connected_devices_file:
    #         connected_devices_file_response = json.load(connected_devices_file)
    #
    #         for devices in connected_devices_file_response["Devices"]:
    #             devices_mac_ids.append(devices["MacAddress"])
    #
    #     print(">>> automation - Current In Memory Device List : " + str(self.active_mac_ids))
    #     print(">>> automation - Updated Connected Device File : " + str(devices_mac_ids))
    #
    #     for device in list(devices_mac_ids):
    #         if device in self.active_mac_ids:
    #             print(">>> automation - Device ", str(device), " already loaded in memory, skipping")
    #             pass
    #         else:
    #             new_devices.append(device)
    #             print(">>> automation - Device ", str(device), "found and added")
    #
    #     self.active_mac_ids = devices_mac_ids
    #     print(">>> automation - Updating GV - In Memory Device List : " + str(self.active_mac_ids))
    #     os.environ['Registered_Devices'] = str(self.active_mac_ids)
    #     print(">>> automation - Updating ENV VAR - In Memory Device List", os.environ.get('Registered_Devices'))
    #     global global_active_mac_ids
    #     global_active_mac_ids = self.active_mac_ids
    #
    #     return new_devices
    #
    # def init_previous_devices(self):
    #     try:
    #         with open(self.connected_devices_file) as connected_devices_file:
    #             connected_devices_file_response = json.load(connected_devices_file)
    #
    #             for devices in connected_devices_file_response["Devices"]:
    #                 self.active_mac_ids.append(devices["MacAddress"])
    #
    #     except Exception as ErrorFileNotFound:
    #         print(f'>>> automation - Error: {ErrorFileNotFound}')
    #         api_json_list = self.get_devicelist()
    #         self.save_device_info(api_json_list)
    #
    #         with open(self.connected_devices_file) as connected_devices_file:
    #             connected_devices_file_response = json.load(connected_devices_file)
    #
    #             for devices in connected_devices_file_response["Devices"]:
    #                 self.active_mac_ids.append(devices["MacAddress"])
    #
    #         print(">>> automation - connected_devices.json file created and loaded into memory")
    #
    #     print(">>> automation - Loading Previously Connected Devices into Global Variable: " + str(self.active_mac_ids))
    #
    #     global global_active_mac_ids
    #     global_active_mac_ids = self.active_mac_ids
    #
    #     connected_devices.ConnectedDevices()

    # def connect_and_stream_data(self, device_mac_id):
    #     print(">>> automation - Starting ConnectAndStream thread for device - ", device_mac_id)
    #     self.connect_and_stream_thread = connect_and_stream.ConnectAndStream(device_mac=device_mac_id)
    #     self.connect_and_stream_thread.start()
    #
    # def reset_automation(self):
    #     pass

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
#         Automation = Automation()
#         Automation.start()
#
#
# main()
