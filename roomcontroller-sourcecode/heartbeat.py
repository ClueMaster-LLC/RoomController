import threading
import os
import json
import time
import platform
import psutil
import requests
import room_controller

from apis import *
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

global HEARTBEAT_STOP
HEARTBEAT_STOP = False


# master class
class Heartbeat(threading.Thread):
    def __init__(self):
        super(Heartbeat, self).__init__()

        # local class attributes
        self.room_id_api_url = None
        self.net_interval = None
        self.net_duration = None
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

        # instance methods
        self.configurations()

        print(f">>> heartbeat - ***STARTUP COMPLETED***")
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

    def execution_environment(self):
        while True:
            try:
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
                # print(f">>> heartbeat - {self.device_unique_id} - HEART BEAT STOP IS: {HEARTBEAT_STOP}")
                if HEARTBEAT_STOP is True:
                    break

            except requests.exceptions.HTTPError as request_error:
                if "401 Client Error" in str(request_error):
                    self.reset_heartbeat()
                    time.sleep(5)
                    break
                else:
                    print(">>> room_controller - " + str(request_error))
                    time.sleep(5)

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

    def reset_heartbeat(self):

        pass

# # Comment out the function when testing from main.py
# def start_thread():
#     if __name__ == "__main__":
#         Heartbeat = Heartbeat()
#         Heartbeat.start()
#
#
# start_thread()
