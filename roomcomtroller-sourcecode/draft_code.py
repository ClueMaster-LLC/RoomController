import threading
import json
import time


class ControllerStatusThread(threading.Thread):
    def __init__(self, room_controller_configs):
        super(ControllerStatusThread, self).__init__()
        print(">>> Console Output - ControllerStatusThread active ...")

        # global attributes
        self.active = None
        self.stopping_thread = False
        self.room_controller_configs = room_controller_configs
        self.registration_thread_instance = None
        self.connect_to_previous_devices_thread_instance = None

    def run(self):
        while True:
            with open(self.room_controller_configs) as configs_file:
                configs_file_response = json.load(configs_file)
                if configs_file_response["reset_room_controller"] is True:
                    self.registration_thread_instance = RegistrationThread()
                    self.registration_thread_instance.stop()
                else:
                    pass

            time.sleep(2)

    def stop(self):
        if self.stopping_thread is False:
            print(">>> Console Output - Stopping Registration Thread")
            self.active = False
            self.stopping_thread = True
            self.run()

        else:
            pass


# wite new found IP to file

son_lastKnownIP_data = {"IP": clientIP}

with open(os.path.join(ROOT_DIRECTORY, "appdata/lastKnownIP.json"), "w") as file:
    json.dump(json_lastKnownIP_data, file)

# Sending a reply to client
# UDPServerSocket.sendto(bytesToSend, address)
