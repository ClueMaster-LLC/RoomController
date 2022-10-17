import json
import threading
import socket
import time
import os
import sys
import ncd_industrial_devices

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

mac = "0008DC21DDFD"



def read_device_info(i_mac):


        deviceList = []
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        with open(device_info_file) as connected_devices_file:
            for jsonObj in connected_devices_file:
                connected_devices_file_response = json.loads(jsonObj)
                deviceList.append(connected_devices_file_response)

        for i in deviceList:
            for devices in i.items():
                #print(devices)
                values = devices[1]
                if values["MacAddress"] == i_mac:
                    print("Device record exists for : ", i_mac)
        return values["IP"], values["DeviceModel"], values["DeviceType"], values["ReadSpeed"]

##            else:
##                # print("Device record does not exist for : ", i_mac)
##                # return ["127.0.0.1", "not_found"]
##                # deviceDiscovery(i_mac)
##                # print("discovery done")
##
##                pass

##    except Exception:
##        print(">>> Console Output - device_info file does not exist or there is improperly formatted data")


read_device_info(mac)
