import json
import os
import platform
import socket
import threading
import time
import sys
import ncd_industrial_devices

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


class AddFindDevices(threading.Thread):
    def __init__(self, **method):
        super(AddFindDevices, self).__init__()

        # global attributes
        self.active = None
        self.method = method

    def run(self):
        if self.method['method'] == 'add':
            # self.ip_connect(self.method['ip'], int(self.method['server_port']), self.method['mac_address'], self.method['device_model'],
            # int(self.method['device_type']), int(self.method['input_total']), int(self.method['relay_total']), float(self.method['read_speed']))
            self.ip_connect(self.method['ip'], int(self.method['server_port']), self.method['mac_address'])
        else:
            self.network_search()

    def ip_connect(self, ip_address, server_port, mac_address):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5.0)
            client_socket.connect((ip_address, server_port))
            try:
                # to clear the buffer on NIC when first connect sends MAC.
                data_response_init = ((list(
                    "{}".format(client_socket.recvfrom(32)[0])[2:-1].replace("\\x00", "").replace(":", "").split(",")))[
                    0])
            except Exception as e:
                print(e)
                data_response_init = 'No data in buffer'
            # print(data_response_init)
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            print('>>> add_find_device - Connecting to ' + str(mac_address))
            data_response = ncd.test_comms()

            if data_response is not None:
                if data_response_init == mac_address:
                    print('>>> add_find_device - Device responded ' + str(mac_address))
                    client_socket.close()
                    print('>>> add_find_device - Return Success to API')
                    return "Success"  # send to API ???? that connection was a success?
                else:
                    print(
                        '>>> add_find_device - Device does not match expected MAC Address: ' + str(data_response_init))
                    return "Fail"

        except Exception as e:
            print(e)
            return "Fail"
            pass

    def network_search(self):
        try:
            localIP = self.extract_ip()
            localPort = 13000
            bufferSize = 1024

            msgFromServer = "Connected"
            bytesToSend = str.encode(msgFromServer)

            # Create a datagram socket
            UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            if platform.system() == "Windows":
                UDPServerSocket.bind((localIP, localPort))
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                # Bind to address and ip
                UDPServerSocket.bind(("<broadcast>", localPort))

            print("add_find_device - UDP server up - Searching Network for Devices ")
            start_time = time.time()
            devices_discovered = []

            # Listen for incoming datagrams
            while True:
                try:
                    bytes_address_pair = UDPServerSocket.recvfrom(bufferSize)
                    # print(bytes_address_pair)
                    # print(list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))
                    # data returned# (b'192.168.1.21,0008DC222A0C,2101,cm_dc48,2.1', ('192.168.1.21', 1460))
                    # or
                    # data returned# (b'192.168.1.19,0008DC21DDFD,2101,cm_dc16,2.2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', ('192.168.1.19', 13000))

                    # discover_ip = ((bytes_address_pair[1])[0])
                    discover_ip = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[0]
                    discover_mac = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[1]
                    discover_port = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[2]
                    discovery_mfr = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[3]
                    discovery_version = \
                        (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[4]
                    # discover_model = self.device_model
                    # discover_device_type = self.device_type

                    if bytes_address_pair is not None:
                        try:
                            print(">>> add_find_device - Discovered Device IP:  ", discover_ip)
                            print(">>> add_find_device - Discovered Device MAC: ", discover_mac)
                            print(">>> add_find_device - Discovered Device Port: ", discover_port)
                            # print(">>> Console Output - Discovered Device Model: ", discover_model)
                            # print(">>> Console Output - Discovered Device Type: ", discover_device_type)
                            print(">>> add_find_device - Discovered Device Network Card Firmware Version: ",
                                  discovery_version)
                            # print(">>> Console Output - Saving updated device info to file.")

                            UDPServerSocket.close()
                            print(">>> add_find_device - Return Success to API")
                            i_device_data = [discover_ip, discover_mac, discover_port]
                            if i_device_data in devices_discovered:
                                pass
                            else:
                                devices_discovered.append(i_device_data)

                            if time.time() - start_time < 15:
                                time.sleep(1)
                                continue
                            else:
                                break

                        except Exception as e:
                            # print(">>> Console Output - Error: Unable to save updated device info to file.")
                            print(e)
                    else:
                        # timer = (timer - 1)
                        # print(timer)
                        print(">>> add_find_device - No devices found on network. Continuing to search...")
                        if time.time() - start_time < 15:
                            time.sleep(1)
                            continue
                        else:
                            break

                    # break
                except socket.error:
                    print(">>> add_find_device - Error trying discovery device")
                    # set connection status and recreate socket
                    # self.connection_lost()
                    self.run()

            print(">>> add_find_device - Devices Found ", devices_discovered)
            return devices_discovered  # return a set of discovered devices in a list [ip, mac, port]

        except socket.error as e:
            print(e)
            print(">>> add_find_device - Error trying to open UDP discovery port")
            # set connection status and recreate socket
            # self.connection_lost()
            self.run()

    @staticmethod
    def extract_ip():
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            st.connect(('10.255.255.255', 1))
            ip_address = st.getsockname()[0]
        except Exception:
            ip_address = '127.0.0.1'
            print(">>> add_find_device - Error trying to find Room Controller IP, Defaulting to 127.0.0.1")
        finally:
            st.close()
        return ip_address

    @staticmethod
    def reboot_device():
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            ncd.device_reboot()
            client_socket.close()
            print(">>> add_find_device - Device Rebooted")

        except Exception:
            print(">>> add_find_device - Error Sending Reboot Command")

    @staticmethod
    def save_device_info(ip, i_mac, server_port, device_model, device_type, read_speed, input_total, relay_total):
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        device_info_dict = {
            "Device1": {"IP": ip, "ServerPort": server_port, "MacAddress": i_mac, "DeviceModel": device_model,
                        "DeviceType": device_type, "ReadSpeed": read_speed,
                        "InputTotal": input_total, "RelayTotal": relay_total}}

        with open(device_info_file, "w") as device_info:
            json.dump(device_info_dict, device_info)


def main():
    if __name__ == "__main__":
        # add_find_device_thread = AddFindDevices(method='add', ip='192.168.1.21', server_port='2101', mac_address='0008DC222A0C')
        add_find_device_thread = AddFindDevices(method='find', ip=None)
        add_find_device_thread.start()


main()
