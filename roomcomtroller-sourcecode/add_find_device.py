import json
import os
import socket
import threading
import time
import sys


class AddFindDevices(threading.Thread):
    def __init__(self, *method):
        super(AddFindDevices, self).__init__()

        # global attributes
        self.active = None
        self.method = method

    def run(self):
        if self.method[0][0] == 'add':
            self.ip_connect(self.method[0][1])
        else:
            self.network_search()

    def ip_connect(self, ip_address):
        pass

    def network_search(self):
        pass


def main():
    if __name__ == "__main__":
        add_find_device_thread = AddFindDevices('find')  # add value for the argument method 'add or find'
        add_find_device_thread.start()


main()
