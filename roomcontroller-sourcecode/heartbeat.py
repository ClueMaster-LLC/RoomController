import time
import os
import json
import socket
import time
import platform
import psutil
# import timeit
import requests
import room_controller

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
        self.net_interval = None
        self.net_duration = None
        self.room_id = None
        self.game_status = None
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



        # Try to Connect to Comhub with SignalR and loop until it does.
        while self.signalr_status is not True:
            try:
                # instance methods
                self.configurations()

                self.signalr_hub()
            except Exception as error:
                print(f">>> heartbeat - {self.device_unique_id} - SignalR Did not connect for Room Controller. "
                      f"Server Error: {error}")
                time.sleep(5)

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
        self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"
        self.signalr_bearer_token = f"?access_token={self.device_unique_id}_{self.api_bearer_key}"
        # self.signalr_access_token = f'?access_token=1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt'

        self.net_interval = 1  # Interval between network measurements in seconds
        self.net_duration = 1  # Duration of network measurement in seconds

        # set the Room ID for the Room Controller to listen to signalR commands
        # TODO remove the wait and pull from the unique_ids file after getting it from a API
        while room_controller.GLOBAL_ROOM_ID is None:
            for i in range(15, -1, -1):
                if room_controller.GLOBAL_ROOM_ID:
                    self.room_id = room_controller.GLOBAL_ROOM_ID
                    print(f">>> heartbeat - {self.device_unique_id} - ROOM ID: {room_controller.GLOBAL_ROOM_ID}")
                    break
                if i == 0:
                    print(f'>>> heartbeat - {self.device_unique_id} - Timeout exceeded. No Room_ID Set.')
                    # break
                print(f'>>> heartbeat - {self.device_unique_id} - waiting for to set Room_ID ... {i}')
                time.sleep(1)
            break

    def signalr_hub(self):
        self.server_url = API_SIGNALR + self.signalr_bearer_token
        print(f">>> heartbeat - {self.device_unique_id} - SignalR connected to {API_SIGNALR}")
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.ERROR)
        self.hub_connection = HubConnectionBuilder() \
            .with_url(self.server_url, options={
            "verify_ssl": True,
            "skip_negotiation": False
        }) \
            .configure_logging(logging.ERROR, socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect({
            "type": "raw",
            "keep_alive_interval": 5,
            "reconnect_interval": 10,
            "max_attempts": 3
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
                                                         f"A Server exception error was thrown: {data.error}")
                                                   )
                                     )
        self.hub_connection.on_open(lambda: (self.hub_connection.send('AddToGroup', [str(self.room_id)]),
                                             self.hub_connection.send('AddToGroup', [str(self.device_unique_id)]),
                                             print(
                                                 f">>> heartbeat - {self.device_unique_id} - signalR "
                                                 f"handshake received. Ready to send/receive messages.")
                                             , self.signalr_connected(True)
                                             )
                                    )
        self.hub_connection.on_reconnect(lambda: (print(f">>> heartbeat - Trying to re-connect to"
                                                        f" {API_SIGNALR}")
                                                  ))

        self.hub_connection.on('ping', (lambda: (print(f">>> heartbeat - {self.device_unique_id} - PING "
                                                       f"command received"), self.ping_response())))

        self.hub_connection.on('restart', (lambda: (print(f">>> heartbeat - {self.device_unique_id} - RESTART "
                                                          f"command received"), self.restart_rc())))

        self.hub_connection.on('shutdown', (lambda: (print(f">>> heartbeat - {self.device_unique_id} - SHUTDOWN "
                                                           f"command received"), self.shutdown_rc())))
        
        self.hub_connection.on('game_status'
                               , (lambda data: (self.set_game_status(data)
                                                , print(f">>> heartbeat - {self.device_unique_id} - "
                                                        f"GameStatus command received. Status = {data}")
                                                )))

        print(f">>> heartbeat - {self.device_unique_id} - starting signalR")

        self.hub_connection.start()
        print(f">>> heartbeat - {self.device_unique_id} - waiting for signalR handshake ...")
        while self.signalr_status is not True:
            try:
                if self.signalr_status is True:
                    break
                else:

                    # print(self.server_url)
                    # print(f'>>> heartbeat - SignalR Status: {self.signalr_status}')
                    time.sleep(0)

            except socket.error as error:
                print(f'>>> heartbeat - {self.device_unique_id} - SignalR connection ERROR ... {error}')
                self.signalr_status = False
                self.hub_connection.stop()
                time.sleep(5)
                self.hub_connection.start()
                time.sleep(5)

        else:
            print(f">>> heartbeat - {self.device_unique_id} - SignalR Connected")

    def set_game_status(self, game_status):
        # command received by hub to refresh values from all device threads to update location workspace
        room_controller.GLOBAL_GAME_STATUS = game_status
        
    def signalr_connected(self, status):
        if status is True:
            self.signalr_status = True
        else:
            self.signalr_status = False

    def execution_environment(self):
        while True:
            # find network utilization
            net_avg_utilization = round(self.get_total_average_utilization(self.net_interval, self.net_duration), 2)
            # print(f"Total average network utilization: {net_avg_utilization} MB/s")

            # Post Device HeartBeat Data to API
            heartbeat_api_url = POST_DEVICE_HEARTBEAT.format(device_id=self.device_unique_id,
                                                             CpuAvg=psutil.cpu_percent(interval=None),
                                                             MemoryAvg=psutil.virtual_memory()[2],
                                                             NetworkAvg=net_avg_utilization)
            requests.post(heartbeat_api_url, headers=self.api_headers)
            print(f">>> heartbeat - {self.device_unique_id} - Device HeartBeat API data sent at {time.ctime()}")

            time.sleep(60)

    def get_network_utilization(self, interval=1):
        net1 = psutil.net_io_counters(pernic=True)
        time.sleep(interval)
        net2 = psutil.net_io_counters(pernic=True)

        utilization = {}
        for nic in net1.keys():
            sent_diff = net2[nic].bytes_sent - net1[nic].bytes_sent
            recv_diff = net2[nic].bytes_recv - net1[nic].bytes_recv
            total_diff = sent_diff + recv_diff
            utilization[nic] = total_diff / (interval * 1024 * 1024)  # Convert to MB/s

        return utilization

    def get_total_average_utilization(self, interval=1, duration=10):
        total_utilization = 0
        count = 0
        start_time = time.time()

        while time.time() - start_time < duration:
            utilization = self.get_network_utilization(interval)
            total_utilization += sum(utilization.values())
            count += 1

        average_utilization = total_utilization / count
        return average_utilization

    def ping_response(self):
        self.hub_connection.send('ping_response', [str(self.device_unique_id), "true"])
        print(f">>> heartbeat - {self.device_unique_id} - PING Response Sent")

    # @staticmethod
    def restart_rc(self):
        try:
            if platform.system() == "Windows":
                # win32api.InitiateSystemShutdown()
                print(f">>> heartbeat - {self.device_unique_id} - Windows Room Controller Rebooting")
                pass
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                os.system('systemctl reboot -i')
            print(f">>> heartbeat - {self.device_unique_id} - Room Controller Rebooting")

        except Exception as error:
            print(f">>> heartbeat - ERROR: {error}")
            print(f">>> heartbeat - {self.device_unique_id} - Error Sending Reboot Command")

    # @staticmethod
    def shutdown_rc(self):
        try:
            if platform.system() == "Windows":
                # win32api.InitiateSystemShutdown()
                print(f">>> heartbeat - {self.device_unique_id} - Windows Room Controller Rebooting")
                pass
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                os.system('systemctl poweroff -i')
            print(f">>> heartbeat - {self.device_unique_id} - Shutting Down Room Controller")

        except Exception as error:
            print(f">>> heartbeat - {self.device_unique_id} - ERROR: {error}")
            print(f">>> heartbeat - {self.device_unique_id} - Error Sending Reboot Command")

# # Comment out the function when testing from main.py
# def start_thread():
#     if __name__ == "__main__":
#         Heartbeat = Heartbeat()
#         Heartbeat.start()
#
#
# start_thread()
