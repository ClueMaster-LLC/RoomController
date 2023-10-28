import os
import json
import threading
import auto_startup
import connected_devices
import automation
import heartbeat

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# BASE VARIABLES


# RegistrationThread checks for device registration
class RegistrationThread(threading.Thread):
    def __init__(self):
        super(RegistrationThread, self).__init__()
        print(">>> thread_manager - RegistrationThread active ....")

        # global attributes
        self.active = None
        self.auto_startup_instance = None

    def run(self):
        self.auto_startup_instance = auto_startup.AutoStartup()
        self.auto_startup_instance.__int__()

        print(">>> thread_manager - Stopped Base Registration Thread ...")
        print(">>> thread_manager - Restarting Room Controller ...")
        restart_room_controller()
        return


# ConnectPreviousDevicesThread connect to previously configured devices
class ConnectPreviousDevicesThread(threading.Thread):
    def __init__(self):
        super(ConnectPreviousDevicesThread, self).__init__()
        print(">>> thread_manager - ConnectPreviousThread active ....")

        # global attributes
        self.active = None
        self.connected_devices_instance = None

    def run(self):
        self.connected_devices_instance = connected_devices.ConnectedDevices()
        # self.connected_devices_instance.__init__()
        print(">>> thread_manager - Stopped Base ConnectPreviousDevicesThread ...")
        return


# AutomationThread connect to run special automations in a separate process
class HeartbeatThread(threading.Thread):
    def __init__(self):
        super(HeartbeatThread, self).__init__()
        print(">>> thread_manager - AutomationThread active ....")

        # global attributes
        self.active = None
        self.heartbeat_instance = None

    def run(self):
        self.heartbeat_instance = heartbeat.Heartbeat()
        print(">>> thread_manager - Stopped Base ConnectPreviousDevicesThread ...")
        return


# AutomationThread connect to run special automations in a separate process
class AutomationThread(threading.Thread):
    def __init__(self):
        super(AutomationThread, self).__init__()
        print(">>> thread_manager - AutomationThread active ....")

        # global attributes
        self.active = None
        self.automation_instance = None

    def run(self):
        self.automation_instance = automation.Automation()
        print(">>> thread_manager - Stopped Base ConnectPreviousDevicesThread ...")
        return


# master thread manager
class ThreadManager:
    def __init__(self):
        super(ThreadManager, self).__init__()

        print(">>> thread_manager - Starting Thread Manager ....")

        # global attributes
        self.active = None
        self.registration_thread = None
        self.heartbeat_thread = None
        self.automation_thread = None
        self.connect_to_previous_device_thread = None
        self.controller_status_thread = None
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.previously_connected_devices_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")

        # instance methods
        self.configurations()
        self.execution_environment()

    def configurations(self):
        print(">>> Global - Master Home Directory - ", APPLICATION_DATA_DIRECTORY)
        if os.path.isdir(APPLICATION_DATA_DIRECTORY) is False:
            os.makedirs(APPLICATION_DATA_DIRECTORY)
            print(">>> thread_manager - Creating connected_devices.json file with default format ...")
            with open(self.previously_connected_devices_file, "w") as connected_devices_files:
                i_dictionary = {"Devices": []}
                json.dump(i_dictionary, connected_devices_files)
        else:
            pass

        with open(self.roomcontroller_configs_file, "w") as configurations_file:
            input_dictionary = {"connect_previous_device_thread_active": True,
                                "registration_thread_active": True}
            json.dump(input_dictionary, configurations_file)

    def execution_environment(self):
        if os.path.isfile(self.previously_connected_devices_file):
            ## LETS START CONNECTED DEVICES() FROM THE ROOM CONTROLLER SO
            ## GLOBAL VARIABLE AN LOAD PRIOR BUT KEEP ELSE LOGIC HERE TO
            ## WRITE A FILE IF ITS MISSING AND REGISTRATION START
            ##            self.connect_to_previous_device_thread = ConnectPreviousDevicesThread()
            ##            self.connect_to_previous_device_thread.start()
            pass
        else:
            with open(self.roomcontroller_configs_file) as configurations_file:
                configurations_file_data = json.load(configurations_file)

            with open(self.roomcontroller_configs_file, "w") as configurations_file:
                configurations_file_data["connect_previous_device_thread_active"] = False
                json.dump(configurations_file_data, configurations_file)

        # starting registration thread
        self.registration_thread = RegistrationThread()
        self.registration_thread.start()

        self.heartbeat_thread = HeartbeatThread()
        self.heartbeat_thread.start()

        # self.automation_thread = AutomationThread()
        # self.automation_thread.start()


def restart_room_controller():
    # triggering main function from main.py
    thread_manager = ThreadManager()
    pass
