import subprocess
import sys
import mpv
import requests
import simplejson.errors
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *
from PyQt5.QtSvg import QSvgWidget
import os
import json
import threads
from requests.structures import CaseInsensitiveDict

# Setting up base directories
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterDisplay")

# Pulling up platform specifications
with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as platform_specs_file:
    PLATFORM = json.load(platform_specs_file)["platform"]


class IdentifyDevice(QWidget):
    def __init__(self):
        super(IdentifyDevice, self).__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()
        self.load_device_address()
        self.API_status = True

        # widgets
        self.font = QFont("Ubuntu")
        self.font.setWordSpacing(2)
        self.font.setLetterSpacing(QFont.AbsoluteSpacing, 1)

        self.master_layout = QVBoxLayout(self)
        self.identify_device_audio_player = QMediaPlayer(self)

        # variables
        self.app_root = os.path.abspath(os.path.dirname(sys.argv[0]))

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as file:
            json_object = json.load(file)

        self.device_unique_code = json_object["Device Unique Code"]

        # full screen shortcut
        fullScreen_shortCut = QShortcut(QKeySequence(Qt.Key_F11), self)
        fullScreen_shortCut.activated.connect(self.go_fullscreen)

        # instance methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """ this method contains the codes for the configuration of the window"""

        self.move(0, 0)
        self.setFixedSize(self.screen_width, self.screen_height)
        self.setStyleSheet("background-color: black;")
        self.setCursor(Qt.BlankCursor)
        self.showFullScreen()

    def load_device_address(self):
        """ this method loads the ipv4 address of the device from the unique code json file"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        initial_addresses = unique_code_response["IPv4 Address"]
        self.ipAddress = initial_addresses.split(" ")[0]

    def go_fullscreen(self):
        """ this method checks if the F11 key is pressed, if yes then check if the window is in full screen mode, if
            yes then put it back to normal else show full screen """

        if self.isFullScreen() is True:
            # window is in full game screen mode
            self.showMaximized()
            self.setCursor(Qt.ArrowCursor)

        else:
            # window is in normal screen mode
            self.setCursor(Qt.BlankCursor)
            self.showFullScreen()

    def keyPressEvent(self, event):
        """ this method is triggered as soon as any button is pressed, this is a builtin event method which has been
            overridden to ignore any input from the keyboard"""

        event.ignore()

    def dragMoveEvent(self, event):
        """ this method is triggered as soon as the window is dragged, this is a builtin event method which has been
            overridden to ignore the drag window command"""

        event.ignore()

    def resizeEvent(self, event):
        """ this method is triggered as soon as the window is resized, this is a builtin event method which has been
            overridden to ignore the resize command"""

        event.ignore()
        
    def frontend(self):
        """ this method contains all the codes for the labels in the identify device window"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/IdentifyDeviceDetails.json")) as file:
            json_object = json.load(file)

        self.font.setPointSize(40)

        self.device_name = QLabel(self)
        self.device_name.setFont(self.font)
        self.device_name.setText(f"DEVICE NAME : {json_object['DisplayText']}")
        self.device_name.setStyleSheet("color:white; font-weight:bold;")

        self.ip_address = QLabel(self)
        self.ip_address.setFont(self.font)
        self.ip_address.setText(f"IP ADDRESS : {self.ipAddress}")
        self.ip_address.setStyleSheet("color:white; font-weight:bold;")

        self.device_key = QLabel(self)
        self.device_key.setFont(self.font)
        self.device_key.setText(f"DEVICE KEY : {self.device_unique_code}")
        self.device_key.setStyleSheet("color:white; font-weight:bold;")

        self.api_status = QLabel(self)
        self.api_status.setFont(self.font)
        self.api_status.setText(f"API STATUS : {self.API_status}")
        self.api_status.setStyleSheet("color:white; font-weight:bold;")

        self.last_api_response_time = QLabel(self)
        self.last_api_response_time.setFont(self.font)
        self.last_api_response_time.setText(f"LAST API RESPONSE : {json_object['Requestdate']}")
        self.last_api_response_time.setStyleSheet("color:white; font-weight:bold;")

        self.master_layout.setSpacing(0)
        self.master_layout.setContentsMargins(int(self.screen_width / 10), int(self.screen_height / 15),
                                              int(self.screen_width / 10), int(self.screen_height / 15))

        self.master_layout.addWidget(self.device_name, alignment=Qt.AlignLeft)
        self.master_layout.addWidget(self.ip_address, alignment=Qt.AlignLeft)
        self.master_layout.addWidget(self.device_key, alignment=Qt.AlignLeft)
        self.master_layout.addWidget(self.api_status, alignment=Qt.AlignLeft)
        self.master_layout.addWidget(self.last_api_response_time, alignment=Qt.AlignLeft)

        audio = os.path.join(ROOT_DIRECTORY, "assets/IdentifyDevice.mp3")

        media_content = QMediaContent(QUrl.fromLocalFile(os.path.join(self.app_root, audio)))
        self.identify_device_audio_player.setMedia(media_content)
        self.identify_device_audio_player.play()

        self.setLayout(self.master_layout)


class GameIdleMPVPlayer(QWidget):

    def __init__(self, file_name):
        super(GameIdleMPVPlayer, self).__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # configs
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WA_NativeWindow)

        # loading mpv configurations
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as master_specs:
            config = json.load(master_specs)["mpv_configurations"]

        # widget
        if PLATFORM == "Intel":
            self.master_animated_image_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/game_idle_image_player_logs.log")
        elif PLATFORM == "AMD":
            self.master_animated_image_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/game_idle_image_player_logs.log")
        else:
            self.master_animated_image_player = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/game_idle_image_player_logs.log")

        # variables
        self.file_name = file_name

        # instance methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """ this method contains code for the configurations of the window"""

        self.resize(self.screen_width, self.screen_height)
        self.setCursor(Qt.BlankCursor)

    def frontend(self):
        """ this method contains the codes for showing the video clue"""

        self.master_animated_image_player.loop = True
        self.master_animated_image_player.play(self.file_name)


class GameIdle(QMainWindow):
    def __init__(self):
        super(GameIdle, self).__init__()

        # default variables and instances
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # threads
        self.identify_device_thread = threads.IdentifyDevice()
        self.identify_device_thread.start()
        self.identify_device_thread.identify_device.connect(self.identify_device)
        self.identify_device_thread.update_detected.connect(self.restart_device)

        self.shutdown_restart_request = threads.ShutdownRestartRequest()
        self.shutdown_restart_request.start()
        self.shutdown_restart_request.shutdown.connect(self.shutdown_device)
        self.shutdown_restart_request.restart.connect(self.restart_device)

        self.update_room_info_thread = threads.UpdateRoomInfo()
        self.update_room_info_thread.start()
        self.update_room_info_thread.update_detected.connect(self.restart_device)

        # widgets
        self.font = QFont("Ubuntu")
        self.font.setWordSpacing(2)
        self.font.setLetterSpacing(QFont.AbsoluteSpacing, 1)

        self.master_background = QLabel(self)

        # variables
        self.shutdownRequestReceived = False
        self.restartRequestReceived = False
        self.isDeviceIdentifying = False
        self.no_media_files = False
        self.mpv_player_triggered = False
        self.app_root = os.path.abspath(os.path.dirname(sys.argv[0]))

        self.font.setWordSpacing(2)
        self.font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        self.setStyleSheet("background-color: #191F26;")

        # apis
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_responses = initial_dictionary

        self.device_unique_code = unique_code_responses["Device Unique Code"]
        self.api_key = unique_code_responses["apiKey"]

        self.room_info_api = "https://deviceapi.cluemaster.io/api/Device/GetRoomInfo/{}".format(self.device_unique_code)

        self.headers = CaseInsensitiveDict()
        self.headers["Authorization"] = f"Basic {self.device_unique_code}:{self.api_key}"

        # instance methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """ this method contains the codes for the configurations of the window """

        self.move(0, 0)
        self.setFixedSize(self.screen_width, self.screen_height)
        self.setCursor(Qt.BlankCursor)

    def frontend(self):
        """this method sets the available background image to the window as the central widget"""

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json")) as configurations_json_file:
                initial_dictionary = json.load(configurations_json_file)

            room_info_response = initial_dictionary
            if self.no_media_files is False:

                if room_info_response["IsPhoto"] is True:
                    # checking if photo is enabled in the webapp
                    self.picture_location = os.path.join(MASTER_DIRECTORY, "assets/room data/picture/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/picture/"))[0]))

                    if self.picture_location.endswith(".apng") or self.picture_location.endswith(".ajpg") or \
                            self.picture_location.endswith(".gif"):

                        self.mpv_player_triggered = True
                        self.external_master_mpv_players = GameIdleMPVPlayer(file_name=self.picture_location)
                        self.external_master_mpv_players.setParent(self)
                        self.external_master_mpv_players.show()

                    elif self.picture_location.endswith(".svg"):

                        self.svg_widget = QSvgWidget(self.picture_location)
                        self.svg_widget.resize(self.screen_width, self.screen_height)
                        self.svg_widget.setParent(self)
                        self.svg_widget.show()

                    else:
                        self.master_background.setPixmap(QPixmap(self.picture_location).scaled(self.screen_width, self.screen_height))
                        self.setCentralWidget(self.master_background)
                else:
                    self.setStyleSheet("background-color:#191F26;")
            else:
                self.setStyleSheet("background-color:#191F26;")

        except json.decoder.JSONDecodeError:
            # if the code inside the try block faces json decode error, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the code inside the try block faces simplejson decode error then pass
            pass

    def identify_device(self, response):
        """ this method is triggered as soon as the identify_device signal is emitted by the identify device thread"""

        print(">>> Identify Response ", response)
        if response == 1:
            # if 1 is emitted by the signal then show the details
            if self.isDeviceIdentifying is False:
                self.identify_device_window = IdentifyDevice()
                self.identify_device_window.show()
                self.isDeviceIdentifying = True

        else:
            # if response is other than 1 then hide the device information
            if self.isDeviceIdentifying is True:
                self.identify_device_window.close()

            else:
                pass

            self.isDeviceIdentifying = False

    def restart_device(self):
        """ this method is triggered as soon as the restart signal is emitted by the shutdown restart thread"""

        if self.restartRequestReceived is False:
            self.restartRequestReceived = True
            
            import dbus

            bus = dbus.SystemBus()
            bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
            bus_object.Reboot(True, dbus_interface="org.freedesktop.login1.Manager")
            
            self.close()

        else:
            pass

    def shutdown_device(self):
        """ this method is triggered as soon as the shutdown signal is emitted by the shutdown restart thread"""

        if self.shutdownRequestReceived is False:
            self.shutdownRequestReceived = True

            import dbus

            bus = dbus.SystemBus()
            bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
            bus_object.PowerOff(True, dbus_interface="org.freedesktop.login1.Manager")

            self.close()

        else:
            pass

    def deleteLater(self):
        """ this method when triggered first closes the identify device window if opened and then close the master
            window"""

        if self.isDeviceIdentifying is True:
            self.identify_device_window.close()

        self.close()

    def stop_threads(self):
        """ this method when triggered stops every threads related to this window"""

        self.identify_device_thread.stop()
        self.shutdown_restart_request.stop()
        self.update_room_info_thread.stop()
