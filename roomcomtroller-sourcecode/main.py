# CLUEMASTER ROOM CONTROLLER
# This is the main.py that will trigger the room controller

# imports
import auto_startup
import os

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


# room controller configurations
def base_configurations():
    roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
    if os.path.isfile(roomcontroller_configs_file):
        pass
    else:
        with open(roomcontroller_configs_file, "w"):
            pass


# master function
def main():
    auto_startup_instance = auto_startup.AutoStartup()
    auto_startup_instance.__int__()


main()
