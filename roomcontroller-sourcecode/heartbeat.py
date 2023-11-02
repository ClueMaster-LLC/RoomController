import os
import json
import socket
import time
import platform

from apis import *
from requests.structures import CaseInsensitiveDict

# This import will be for signalR code##
import logging
from signalrcore.hub_connection_builder import HubConnectionBuilder
from signalrcore.protocol.messagepack_protocol import MessagePackHubProtocol

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# master class
class Heartbeat:
    def __init__(self):
        super(Heartbeat, self).__init__()

        # local class attributes
        self.hub_connection = None
        self.handler = None
        self.server_url = None
        self.signalr_bearer_token = None
        self.device_request_api_url = None
        self.api_bearer_key = None
        self.device_unique_id = None
        self.api_token = None
        self.api_headers = None
        self.signalr_status = None
        self.api_active_null_responses = ["No room controller found", "No request found", "No record found",
                                          "No record found in inventory master"]

        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")

        # instance methods
        self.configurations()

        try:
            self.signalr_hub()
        except Exception as error:
            print(
                f">>> heartbeat - {self.device_unique_id} - SignalR Did not connect for Device. Server Error: {error}")

        print(f">>> heartbeat - {self.device_unique_id} - ***STARTUP COMPLETED***")
        self.execution_environment()
        print(">>> heartbeat - **********  HEARTBEAT THREAD SHUTTING DOWN  **********")

    def configurations(self):
        try:
            # Load the device ID's from the JSON file
            with open(self.unique_ids_file) as unique_ids_file:
                json_response_of_unique_ids_file = json.load(unique_ids_file)

        except Exception as ErrorFileNotFound:
            print(f'>>> automation - Error: {ErrorFileNotFound}')

        self.device_unique_id = json_response_of_unique_ids_file["device_id"]
        self.api_bearer_key = json_response_of_unique_ids_file["api_token"]
        self.device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

        self.api_headers = CaseInsensitiveDict()
        # self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"
        self.signalr_bearer_token = f"?access_token={self.device_unique_id}_{self.api_bearer_key}"
        # self.signalr_access_token = f'?access_token=1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt'

    def signalr_hub(self):
        self.server_url = API_SIGNALR + self.signalr_bearer_token
        print(f">>> connect_and_stream - {self.device_unique_id} - SignalR connected to {API_SIGNALR}")
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.ERROR)
        self.hub_connection = HubConnectionBuilder() \
            .with_url(
            self.server_url, options={"verify_ssl": True, "skip_negotiation": False}) \
            .configure_logging(logging.ERROR, socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect(
            {
                "type": "raw",
                "keep_alive_interval": 5,
                "reconnect_interval": 5.0,
                "max_attempts": 99
            }).build()
        # TODO try to get retries working and connect to signalR when online
        # "accessTokenFactory": 'value'
        # "http_client_options": {"headers": self.api_headers, "timeout": 5.0},
        # "ws_client_options": {"headers": self.api_headers, "timeout": 5.0}
        # "type": "raw",
        # "type": "interval",
        # "keep_alive_interval": 5,
        # "reconnect_interval": 5,
        # "max_attempts": 99999999,
        # "intervals": [1, 3, 5, 6, 7, 87, 3]
        # .with_hub_protocol(MessagePackHubProtocol()) \

        self.hub_connection.on_close(lambda: (print(f">>> heartbeat - {self.device_unique_id} - SignalR "
                                                    f"Connection Closed"), self.signalr_connected(False)
                                              ))
        self.hub_connection.on_error(lambda data: (print(f">>> heartbeat - {self.device_unique_id} - "
                                                         f"An exception was thrown: {data.error}")))
        self.hub_connection.on_open(lambda: (self.hub_connection.send('AddToGroup', [str(self.device_unique_id)]),
                                             print(
                                                 f">>> heartbeat - {self.device_unique_id} - signalR "
                                                 f"handshake received. Ready to send/receive messages.")
                                             , self.signalr_status is True
                                             )
                                    )
        self.hub_connection.on_reconnect(lambda: (print(f">>> heartbeat - Trying to re-connect to"
                                                        f" {API_SIGNALR}")
                                                  ))

        self.hub_connection.on('ping', (lambda data: (print(f">>> heartbeat - {self.device_unique_id} - PING "
                                                            f"command received"), self.ping_response())))

        print(">>> heartbeat - starting signalR")

        print(f'>>> heartbeat - signalR status: {self.signalr_status}')
        while self.signalr_status is not True:
            try:
                self.hub_connection.start()

                if self.signalr_status is True:
                    break
                else:
                    print(f'>>> heartbeat - {self.device_unique_id} - waiting for signalR handshake ...')
                time.sleep(5)

            except socket.error as error:
                print(f'>>> heartbeat - {self.device_unique_id} - SignalR connection ERROR ... {error}')
                self.signalr_status = False
                self.hub_connection.stop()
                time.sleep(5)

        else:
            print(">>> heartbeat - signalr connected")



    def signalr_connected(self, status):
        if status is True:
            self.signalr_status = True
        elif not status:
            self.signalr_status = False

    @staticmethod
    def execution_environment():
        while True:
            print(">>> heartbeat - waiting for heartbeat action")
            time.sleep(5)
            # run heartbeat logic here

    def ping_response(self):
        self.hub_connection.send('heartbeat', [str(self.device_unique_id), "true"])
        print(f">>> heartbeat - {self.device_unique_id} - PING Response Sent")

    @staticmethod
    def reboot_rc():
        try:
            if platform.system() == "Windows":
                # win32api.InitiateSystemShutdown()
                print(">>> heartbeat - Windows Room Controller Rebooting")
                pass
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                os.system('systemctl reboot -i')
            print(">>> heartbeat - Room Controller Rebooting")

        except Exception as error:
            print(f">>> heartbeat - ERROR: {error}")
            print(">>> heartbeat - Error Sending Reboot Command")

# Comment out the function when testing from main.py
# def start_thread():
#     if __name__ == "__main__":
#         Heartbeat = Heartbeat()
#         Heartbeat.start()
#
#
# start_thread()
