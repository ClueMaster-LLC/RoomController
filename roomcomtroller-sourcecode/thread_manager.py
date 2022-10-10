import os
import json
import threading
import time
import auto_startup
import connected_devices

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# RegistrationThread checks for device registration
class RegistrationThread(threading.Thread):
    def __init__(self):
        super(RegistrationThread, self).__init__()
        print(">>> Console Output - RegistrationThread active ....")

        # global attributes
        self.active = None
        self.auto_startup_instance = None

    def run(self):
        self.auto_startup_instance = auto_startup.AutoStartup()
        self.auto_startup_instance.__int__()

        print(">>> Console Output - Stopped Base RegistrationThread ...")
        print(">>> Console Output - Restarting Room Controller ...")
        restart_room_controller()
        return


# ConnectPreviousDevicesThread connect to previously configured devices
class ConnectPreviousDevicesThread(threading.Thread):
    def __init__(self):
        super(ConnectPreviousDevicesThread, self).__init__()
        print(">>> Console Output - ConnectPreviousThread active ....")

        # global attributes
        self.active = None
        self.connected_devices_instance = None

    def run(self):
        self.connected_devices_instance = connected_devices.ConnectedDevices()
        self.connected_devices_instance.__init__()
        print(">>> Console Output - Stopped Base ConnectPreviousDevicesThread ...")
        return


# master thread manager
class ThreadManager:
    def __init__(self):
        super(ThreadManager, self).__init__()
        print(">>> Console Output - Starting Thread Manager ....")

        # global attributes
        self.active = None
        self.registration_thread = None
        self.connect_to_previous_device_thread = None
        self.controller_status_thread = None
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.previously_connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        if os.path.isdir(APPLICATION_DATA_DIRECTORY) is False:
            os.makedirs(APPLICATION_DATA_DIRECTORY)
        else:
            pass

        with open(self.roomcontroller_configs_file, "w") as configurations_file:
            input_dictionary = {"connect_previous_device_thread_active": True,
                                "registration_thread_active": True}
            json.dump(input_dictionary, configurations_file)

    def execution_environment(self):
        time.sleep(2)

        if os.path.isfile(self.previously_connected_devices_file):
            self.connect_to_previous_device_thread = ConnectPreviousDevicesThread()
            self.connect_to_previous_device_thread.start()
        else:
            with open(self.roomcontroller_configs_file) as configurations_file:
                configurations_file_data = json.load(configurations_file)

            with open(self.roomcontroller_configs_file, "w") as configurations_file:
                configurations_file_data["connect_previous_device_thread_active"] = False
                json.dump(configurations_file_data, configurations_file)

        # starting registration thread
        self.registration_thread = RegistrationThread()
        self.registration_thread.start()


def restart_room_controller():
    # triggering main function from main.py
    thread_manager = ThreadManager()
