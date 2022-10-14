import json
import os
import socket
import threading
import time
import sys


class AddFindDevices(threading.Thread):
    def __init__(self):
        super(AddFindDevices, self).__init__()

        # global attributes
        self.active = None

    def run(self):
        pass


def main():
    if __name__ == "__main__":
        add_find_device_thread = AddFindDevices()
        add_find_device_thread.start()


main()
