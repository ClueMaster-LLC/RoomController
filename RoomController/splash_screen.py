import os
import json
import uuid
import re
import random
import time
import subprocess
import locale
import requests
from string import Template
from requests.structures import CaseInsensitiveDict
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QMovie, QIcon
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QDesktopWidget

# Setting up the base directories
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterDisplay")

# Setting up environment variables (uncomment if warnings popup again)

# del os.environ["GTK_MODULES"]
# del os.environ["SESSION_MANAGER"]
# os.environ["QT_QPA_PLATFORMTHEME"] = "gtk2"

snap_version = os.environ.get("SNAP_VERSION")


class SplashBackend(QThread):
    skip_authentication = pyqtSignal(bool)

    def __init__(self):
        super(SplashBackend, self).__init__()

        # default variables
        self.is_killed = False

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        time.sleep(2)

        if os.path.isdir(os.path.join(MASTER_DIRECTORY, "assets/application data")) is False:
            # if there is no directory named application data inside the assets directory then create one
            os.makedirs(os.path.join(MASTER_DIRECTORY, "assets/application data"))
        else:
            # if the directory already exists then pass
            pass

        if os.path.isfile(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")):
            # checking if unique code.json file exists in the application data directory, if yes then get the unique
            # device id and check if there are any device files for it

            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
                json_object_of_unique_code_file = json.load(unique_code_json_file)

            device_unique_code = json_object_of_unique_code_file["Device Unique Code"]
            api_key = json_object_of_unique_code_file["apiKey"]
            device_files_url = f"https://deviceapi.cluemaster.io/api/Device/GetDeviceFiles/{device_unique_code}"

            while self.is_killed is False:
                print(">>> Console output - Splash Screen Backend")
                try:
                    headers = CaseInsensitiveDict()
                    headers["Authorization"] = f"Basic {device_unique_code}:{api_key}"

                    if requests.get(device_files_url, headers=headers).status_code != 200:
                        # if response is 401 from the GetDeviceFiles api then, register the device
                        self.skip_authentication.emit(False)

                    else:
                        # else jump to loading screen
                        self.skip_authentication.emit(True)

                    ipv4_address = self.fetch_ipv4_device_address()
                    json_object_of_unique_code_file["IPv4 Address"] = ipv4_address

                    with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json"), "w") as unique_code_json_file:
                        json.dump(json_object_of_unique_code_file, unique_code_json_file)

                except requests.exceptions.ConnectionError:
                    # if api call is facing connection error, wait for 2 seconds and then retry
                    time.sleep(2)
                    continue

                else:
                    break

        else:
            # if there is no unique code.json file then generate an unique device id and secure api key and then save
            # them to unique code.json file and register device

            with open("/proc/cpuinfo") as master_cpu_info_file:
                file_data = master_cpu_info_file.read()

                if "hypervisor" in file_data:
                    dictionary = {"platform": "VirtualMachine", "mpv_configurations": {"vo": "x11"}}
                elif "Intel" in file_data:
                    dictionary = {"platform": "Intel", "mpv_configurations": {"hwdec": "auto", "vo": "gpu", "gpu_context": "auto"}}
                elif "AMD" in file_data:
                    dictionary = {"platform": "AMD", "mpv_configurations": {"hwdec": "auto", "vo": "gpu", "gpu_context": "auto"}}
                else:
                    dictionary = {"platform": "Unspecified"}

                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json"), "w") as specs_file:
                    json.dump(dictionary, specs_file)

            numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
            alphabets = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
                         "T", "U", "V", "W", "X", "Y", "Z"]

            random_pair = [random.choice(alphabets), random.choice(numbers), random.choice(alphabets),
                           random.choice(numbers)]
            get_raw_mac = ':'.join(re.findall('..', '%012x' % uuid.getnode())).replace(":", "").upper()

            splitting_each_character = [character for character in get_raw_mac]

            first_pair = "".join(splitting_each_character[:4])
            second_pair = "".join(splitting_each_character[4:8])
            third_pair = "".join(splitting_each_character[8:12])
            fourth_pair = "".join(random_pair)

            full_unique_code = first_pair + "-" + second_pair + "-" + third_pair + "-" + fourth_pair
            api_key = self.generate_secure_api_key(device_id=full_unique_code)
            ipv4_address = self.fetch_ipv4_device_address()

            json_object = {"Device Unique Code": full_unique_code, "apiKey": api_key, "IPv4 Address": ipv4_address}
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json"), "w") as file:
                json.dump(json_object, file)

            self.skip_authentication.emit(False)

    def generate_secure_api_key(self, device_id):
        """ this method takes the device_id and then generates a secure api key for it"""

        while True:
            try:
                authentication_api_url = "https://deviceapi.cluemaster.io/api/Auth/PostGenerateApiKey"
                device_id = device_id

                headers = CaseInsensitiveDict()
                headers["Content-Type"] = "application/json"

                initial_template = Template("""{"DeviceKey": "${device_key}", "Username": "ClueMaster", "Password": "User_123"}""")
                data = initial_template.substitute(device_key=device_id)

                response = requests.post(url=authentication_api_url, headers=headers, data=data).json()
                print(">>> Console output - API Auth status - ", response["status"])
                return response["apiKey"]

            except requests.exceptions.ConnectionError:
                time.sleep(3)
                pass

    def fetch_ipv4_device_address(self):
        """ this method fetches the device ipv4 address"""

        initial_output = subprocess.getoutput("hostname -I")
        return initial_output

    def stop(self):
        """ this method stops the thread by setting the is_killed attribute to False and then calling the run() methods
            which when validated with a while loop turns False and thus breaks"""

        self.is_killed = True
        self.run()


class SplashWindow(QWidget):
    def __init__(self):
        super().__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # widgets
        self.font = QFont("Ubuntu", 19)

        # instance methods
        self.window_config()
        self.frontend()

    def window_config(self):
        """ this method contains code for the configurations of the window"""

        self.font.setWordSpacing(2)
        self.font.setLetterSpacing(QFont.AbsoluteSpacing, 1)

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        self.setFixedHeight(int(self.screen_height // 2.5))
        self.setFixedWidth(int(self.screen_width // 2.75))
        self.setWindowIcon(QIcon("assets/icons/app_icon.png"))
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color:#191F26; color:white;")

    def frontend(self):
        """ this methods holds the codes for the different labels and animations"""

        self.main_layout = QVBoxLayout()

        application_name = QLabel(self)
        application_name.setFont(self.font)
        application_name.setText("ClueMaster TV Display Timer")
        application_name.setStyleSheet("color: white; font-weight:bold;")

        version = QLabel(self)
        version.setText(f"Version : {snap_version}")
        version.setFont(self.font)
        version.setStyleSheet("color: white; font-size: 19px; font-weight:bold;")

        gif = QMovie(os.path.join(ROOT_DIRECTORY, "assets/icons/security_loading.gif"))
        gif.start()

        loading_gif = QLabel(self)
        loading_gif.setMovie(gif)
        loading_gif.show()

        self.main_layout.addSpacing(self.height() // 9)
        self.main_layout.addWidget(application_name, alignment=Qt.AlignCenter)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(version, alignment=Qt.AlignCenter)
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(loading_gif, alignment=Qt.AlignCenter)

        self.setLayout(self.main_layout)
        self.connect_backend_thread()

    def connect_backend_thread(self):
        """ this method starts the splash screen backend thread """

        self.splash_thread = SplashBackend()
        self.splash_thread.start()
        self.splash_thread.skip_authentication.connect(self.switch_window)

    def switch_window(self, skip):
        """ this method is triggered as soon as the skip_authentication signal is emitted by the backend thread"""

        self.splash_thread.stop()

        if skip is True:
            # if True is emitted by the skip_authentication signal then, jump to loading screen
            import loading_screen
            self.i_window = loading_screen.LoadingScreen()
            self.i_window.show()
            self.deleteLater()

        else:
            if skip is False:
                # if False if emitted by the skip_authentication signal then, have the device authenticated
                import authentication_screen
                self.i_window = authentication_screen.AuthenticationWindow()
                self.i_window.show()
                self.deleteLater()


def main():
    application = QApplication([])
    locale.setlocale(locale.LC_NUMERIC, 'C')
    application.setApplicationVersion(snap_version)
    application.setApplicationDisplayName("Escape Room Application")
    window = SplashWindow()
    window.show()
    application.exec_()


main()
