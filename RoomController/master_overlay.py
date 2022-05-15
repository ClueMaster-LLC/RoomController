import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import requests
import threads
import time
import json
import subprocess
from requests.structures import CaseInsensitiveDict

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterDisplay")


class CustomIconLabel(QLabel):
    def __init__(self):
        super(CustomIconLabel, self).__init__()

    def setOpacity(self, value, pixmap):

        clue_used_image = QPixmap(pixmap)
        clue_used_image.fill(Qt.transparent)

        painter = QPainter(clue_used_image)
        painter.setOpacity(value)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        self.setPixmap(clue_used_image.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class ClueContainer(QWidget):

    def __init__(self):
        super(ClueContainer, self).__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # variables
        self.row = 0
        self.column = 0
        self.total_space_used = 0
        self.row_restored = False

        # widgets
        self.clue_icon_item = QPixmap(os.path.join(ROOT_DIRECTORY, "assets/icons/clue_icon.png"))
        self.clue_icon_unavailable_item = QPixmap(os.path.join(ROOT_DIRECTORY, "assets/icons/clue_icon_unavailable.png"))

        self.puzzle_clue_icon_1 = CustomIconLabel()
        self.puzzle_clue_icon_2 = CustomIconLabel()
        self.puzzle_clue_icon_3 = CustomIconLabel()
        self.puzzle_clue_icon_4 = CustomIconLabel()
        self.puzzle_clue_icon_5 = CustomIconLabel()
        self.puzzle_clue_icon_6 = CustomIconLabel()
        self.puzzle_clue_icon_7 = CustomIconLabel()
        self.puzzle_clue_icon_8 = CustomIconLabel()
        self.puzzle_clue_icon_9 = CustomIconLabel()
        self.puzzle_clue_icon_10 = CustomIconLabel()

        self.clue_icon_objects = [self.puzzle_clue_icon_1, self.puzzle_clue_icon_2, self.puzzle_clue_icon_3,
                                  self.puzzle_clue_icon_4, self.puzzle_clue_icon_5, self.puzzle_clue_icon_6,
                                  self.puzzle_clue_icon_7, self.puzzle_clue_icon_8, self.puzzle_clue_icon_9,
                                  self.puzzle_clue_icon_10]

        self.clue_icons_available = []

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json")) as device_configurations_json_file:
            initial_dictionary = json.load(device_configurations_json_file)

        self.device_configurations_response = initial_dictionary

        clues_appended = 0
        for widget in self.clue_icon_objects:
            if clues_appended != self.device_configurations_response["Maximum Number Of Clues"]:
                self.clue_icons_available.append(widget)
                clues_appended += 1

            else:
                break

        # instance methods
        self.window_configurations()
        self.puzzle_clue_icon_container()

    def window_configurations(self):
        """ this method contains code for the configurations of the window"""

        self.resize(self.screen_width, self.screen_height)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setCursor(Qt.BlankCursor)

    def update_clues_used(self, used):
        """ this method is triggered after every 7 seconds and it checks if the number of clues used has changed in
            the GetGameDetails api, if yes then updates them in the application too """

        print(">>> Console output - Update clues used")

        clues_used = used
        clues_marked_used = 0

        for icons in self.clue_icons_available:
            icons.setPixmap(self.clue_icon_item.scaled(icons.width(), icons.height(), Qt.KeepAspectRatio,
                                                       Qt.SmoothTransformation))

        for icons in self.clue_icons_available[::-1]:
            if clues_used != clues_marked_used:

                icons.setOpacity(0.4, self.clue_icon_unavailable_item)
                clues_marked_used += 1

            else:
                break

    def puzzle_clue_icon_size_determiner(self):
        """ this method when called, determines the size of the clue icons and returns the size"""

        clue_icon_size = self.device_configurations_response["Clue Size On Screen"]

        if clue_icon_size == 0:
            clue_icon_size = self.screen_width / 16
            return clue_icon_size

        elif clue_icon_size == 1:
            clue_icon_size = self.screen_width / 14
            return clue_icon_size

        elif clue_icon_size == 2:
            clue_icon_size = self.screen_width / 12
            return clue_icon_size

        elif clue_icon_size == 3:
            clue_icon_size = self.screen_width / 10
            return clue_icon_size

        else:
            pass

    def puzzle_clue_icon_container(self):
        """ this method holds the code blocks that creates the clue icons"""

        clue_icon_position = self.device_configurations_response["Clue Position Vertical"]

        if clue_icon_position == "Right":
            # if the requested position of the clue icons is Right then run the following block
            self.master_clue_icon_container_layout = QGridLayout()
            self.master_clue_icon_container_layout.setAlignment(Qt.AlignRight)

            self.row = 0
            self.column = 1

        elif clue_icon_position == "Left":
            # if the requested position of the clue icons is Left then run the following block
            self.master_clue_icon_container_layout = QGridLayout()
            self.master_clue_icon_container_layout.setAlignment(Qt.AlignLeft)

        elif clue_icon_position == "Top":
            # if the requested position of the clue icons is Top then run the following block
            self.master_clue_icon_container_layout = QHBoxLayout(self)
            self.master_clue_icon_container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        elif clue_icon_position == "Bottom":
            # if the requested position of the clue icons is Bottom then run the following block
            self.master_clue_icon_container_layout = QHBoxLayout(self)
            self.master_clue_icon_container_layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        else:
            pass

        self.master_clue_icon_container_layout.setSpacing(0)
        self.master_clue_icon_container_layout.setContentsMargins(0, 0, 0, 0)

        clue_icon_size = self.puzzle_clue_icon_size_determiner()

        self.puzzle_clue_icon_1.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_1.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_2.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_2.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_3.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_3.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_4.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_4.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_5.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_5.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_6.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_6.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_7.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_7.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_8.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_8.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_9.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_9.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.puzzle_clue_icon_10.setFixedSize(QSize(int(clue_icon_size), int(clue_icon_size)))
        self.puzzle_clue_icon_10.setPixmap(self.clue_icon_item.scaled(
            int(clue_icon_size), int(clue_icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # adding the widgets to the layouts
        number_of_clues = self.device_configurations_response["Maximum Number Of Clues"]
        number_of_clues_added = 0

        widgets = [self.puzzle_clue_icon_1, self.puzzle_clue_icon_2, self.puzzle_clue_icon_3, self.puzzle_clue_icon_4,
                   self.puzzle_clue_icon_5, self.puzzle_clue_icon_6, self.puzzle_clue_icon_7, self.puzzle_clue_icon_8,
                   self.puzzle_clue_icon_9, self.puzzle_clue_icon_10]

        if clue_icon_position in ["Top", "Bottom"]:
            for icons in widgets:
                if number_of_clues_added != number_of_clues:
                    self.master_clue_icon_container_layout.addWidget(icons)
                    number_of_clues_added += 1
                else:
                    break
        else:
            for icons in widgets:
                if number_of_clues_added != number_of_clues:
                    space_available = int(self.screen_height - self.total_space_used)

                    if space_available >= clue_icon_size:
                        self.master_clue_icon_container_layout.addWidget(icons, self.row, self.column)
                        self.total_space_used += clue_icon_size
                        number_of_clues_added += 1
                        self.row += 1

                    else:
                        if clue_icon_position == "Right":
                            self.column = 0
                        else:
                            self.column = 1

                        if self.row_restored is False:
                            self.row_restored = True
                            self.row = 0

                        self.master_clue_icon_container_layout.addWidget(icons, self.row, self.column)
                        self.total_space_used += clue_icon_size
                        number_of_clues_added += 1
                        self.row += 1

                else:
                    break

        self.setLayout(self.master_clue_icon_container_layout)


class MasterOverlay(QWidget):

    game_ended = pyqtSignal()

    def __init__(self):
        super(MasterOverlay, self).__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # threads
        self.timer_request_thread = threads.GetTimerRequest()
        self.timer_request_thread.start()
        self.timer_request_thread.updateTimer.connect(self.update_application_timer)
        self.timer_request_thread.update_detected.connect(self.restart_device)

        # widgets
        self.master_layout = QVBoxLayout(self)
        self.countup_label = QLabel(self)
        self.countdown_label = QLabel(self)

        self.countdown_timer = QTimer()
        self.countdown_timer.setTimerType(Qt.PreciseTimer)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown_timer)

        self.countup_timer = QTimer()
        self.countup_timer.setTimerType(Qt.PreciseTimer)
        self.countup_timer.setInterval(1000)
        self.countup_timer.timeout.connect(self.update_countup_timer)

        # variables
        self.is_countdown_timer_active = False
        self.is_countup_timer_active = False

        # apis
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
            initial_dictionary = json.load(game_details_json_file)

        self.game_id = initial_dictionary["gameId"]

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        self.device_id = initial_dictionary["Device Unique Code"]
        self.api_key = initial_dictionary["apiKey"]

        # headers
        self.headers = CaseInsensitiveDict()
        self.headers["Authorization"] = f"Basic {self.device_id}:{self.api_key}"

        # instance methods
        self.window_configurations()
        self.load_application_timer()

    def window_configurations(self):
        """ this method contains the codes for the configurations of the window """

        self.resize(self.screen_width, self.screen_height)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.BlankCursor)
        self.showFullScreen()

    def update_application_timer(self):
        """ this method is triggered as soon as the update_timer signal is emitted by the timer request thread, this
            method updates the application timer with the new value from the GetGameTimer api"""

        self.timer_value_from_api = self.fetch_cloud_timer()

    def restart_device(self):
        """ this method is triggered as soon as the restart signal is emitted by the shutdown restart thread"""
        import dbus

        bus = dbus.SystemBus()
        bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
        bus_object.Reboot(True, dbus_interface="org.freedesktop.login1.Manager")

        self.close()

    def load_application_timer(self):
        """ this method is triggered as soon as the MasterOverlay window is initialized, this method determines if the
            timer is a countdown timer or a countup timer and calls the respective method"""

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json")) as device_configurations_json_file:
                initial_dictionary = json.load(device_configurations_json_file)

            room_info_response = initial_dictionary
            timer_parameter = room_info_response["Time Limit"]

            if timer_parameter >= 1:
                self.timer_value_from_api = self.fetch_cloud_timer()
                self.application_countdown_timer()
            else:
                self.application_countup_timer()

        except json.decoder.JSONDecodeError:
            # if the codes inside the try block faces json decode error then pass
            pass

    def fetch_cloud_timer(self):
        """ this method when called fetches the latest timer value from the GetGameTimer api and returns it"""

        self.get_game_timer_api = "https://deviceapi.cluemaster.io/api/Device/GetGameTimer/{}".format(self.game_id)

        try:
            # getting the timer value from the api
            get_game_timer_response = requests.get(self.get_game_timer_api, headers=self.headers).json()
            timer_value_from_api = int(get_game_timer_response["timer"]) + 1
            return timer_value_from_api

        except requests.exceptions.ConnectionError:
            # if the application faces connection error while making the api call then pass or do nothing
            pass

        except json.decoder.JSONDecodeError:
            # if the application faces json decode error anyhow then do nothing / pass
            pass

    def application_countdown_timer(self):
        """ this method is fully dedicated to the countdown timer"""

        self.is_countdown_timer_active = True

        self.countdown_label.setFont(QFont("Ubuntu", int(self.screen_height / 5.25)))
        self.countdown_label.setStyleSheet("""QLabel{color:white; font-weight:bold;}""")
        self.master_layout.addWidget(self.countdown_label, alignment=Qt.AlignCenter)
        self.countdown_label.show()

        if self.timer_value_from_api < 0:
            self.countdown_label.setText("00:00:00")
            self.game_ended.emit()

        else:
            self.countdown_timer.start()

    def update_countdown_timer(self):
        """ this method is triggered every 1 second to update the countdown timer"""

        if self.timer_value_from_api >= 1:
            self.timer_value_from_api -= 1
            hours_minutes_seconds_format = time.strftime("%H:%M:%S", time.gmtime(self.timer_value_from_api))
            self.countdown_label.setText(hours_minutes_seconds_format)

        else:
            self.countdown_timer.stop()
            self.game_ended.emit()

    def application_countup_timer(self):
        """ this method is fully dedicated to the countup timer"""

        self.is_countup_timer_active = True
        self.timer_value_from_api = self.fetch_cloud_timer()

        self.countup_label.setFont(QFont("Ubuntu", int(self.screen_height / 5.25)))
        self.countup_label.setStyleSheet("""QLabel{color:white; font-weight:bold;}""")
        self.master_layout.addWidget(self.countup_label, alignment=Qt.AlignCenter)
        self.countup_label.show()

        self.countup_timer.start()

    def update_countup_timer(self):
        """ this method is triggered every 1 second to update the countup timer"""

        self.timer_value_from_api += 1
        hours_minutes_seconds_format = time.strftime("%H:%M:%S", time.gmtime(self.timer_value_from_api))
        self.countup_label.setText(hours_minutes_seconds_format)

