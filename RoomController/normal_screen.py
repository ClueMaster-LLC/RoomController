import os
import mpv
import time
import json
from PyQt5.QtSvg import QSvgWidget
import authentication_screen
import threads
import requests
import game_idle
import master_overlay
import clue_containers
import simplejson.errors
from requests.structures import CaseInsensitiveDict
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# Setting up base directories
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterDisplay")

# Pulling up platform specifications
with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as platform_specs_file:
    PLATFORM = json.load(platform_specs_file)["platform"]


class NetworkStatus(QMainWindow):

    def __init__(self):
        super(NetworkStatus, self).__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # widgets
        self.master_widget = QLabel(self)
        self.master_widget.resize(self.screen_width, self.screen_height)

        # instance methods
        self.window_configurations()

    def window_configurations(self):
        """this method contains all the configurations related to the window"""

        self.resize(self.screen_width, self.screen_height)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setCursor(Qt.BlankCursor)

    def frontend(self):
        """this method contains all the codes for setting border of the app red or transparent """

        self.master_widget.setStyleSheet("border: 5px solid; border-color: rgb(240, 14, 14); ")
        self.master_widget.show()
        self.showFullScreen()


class CheckTimerRequestThread(QThread):
    proceed = pyqtSignal()

    def run(self):

        # fetching device key and api key
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary_of_unique_code = json.load(unique_code_json_file)

        self.device_id = initial_dictionary_of_unique_code["Device Unique Code"]
        self.api_key = initial_dictionary_of_unique_code["apiKey"]

        # api headers
        self.headers = CaseInsensitiveDict()
        self.headers["Authorization"] = f"Basic {self.device_id}:{self.api_key}"

        # get timer request api
        self.get_timer_request_api = "https://deviceapi.cluemaster.io/api/Device/GetTimerRequest/{}".format(self.device_id)

        while True:
            try:
                print(">>> Console output - Checking timer request response ")
                response = requests.get(self.get_timer_request_api, headers=self.headers)
                print("Response - ", response.text)
                request_id = response.json()["DeviceRequestid"]
                requests.post("https://deviceapi.cluemaster.io/api/Device/{}/{}".format(self.device_id, request_id), headers=self.headers)

                self.proceed.emit()
                return

            except requests.exceptions.ConnectionError:
                # if the codes inside the try block faces connection error, then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the codes inside the try block faces JSONDecodeError, then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the codes inside the try block faces simplejson DecodeError, then pass
                pass

            finally:
                time.sleep(1.5)


class EndAudioMediaWidget(QMainWindow):

    def __init__(self, file_name):
        super(EndAudioMediaWidget, self).__init__()

        # widgets
        self.master_audio_player = mpv.MPV()

        # variables
        self.file = file_name

        # methods
        self.frontend()
        self.window_configurations()

    def window_configurations(self):
        """this method contains the configurations of the window"""

        self.hide()

    def frontend(self):
        """ this method contains the codes for playing the audio clue"""

        self.master_audio_player.play(self.file)
        self.master_audio_player.register_event_callback(self.verify_status_of_master_audio_player)

    def verify_status_of_master_audio_player(self, event):
        """ this method is triggered with every event emitted by the media player"""

        current_event_id = event["event_id"]
        end_of_file_event_id = 7

        if current_event_id == end_of_file_event_id:
            # if the current media player event matches with the end of file event id then emit the clue_video_ended
            # signal and then close the window
            try:
                self.master_audio_player.quit()
                self.close()

            except RuntimeError:
                pass
        else:
            pass


class EndMediaWidget(QWidget):

    def __init__(self, file_name):
        super(EndMediaWidget, self).__init__()

        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # configs
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WA_NativeWindow)

        # loading mpv configurations
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as master_specs:
            config = json.load(master_specs)["mpv_configurations"]

        # widgets
        if PLATFORM == "Intel":
            self.end_media_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/end_video_logs.log")
        elif PLATFORM == "AMD":
            self.end_media_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/end_video_logs.log")
        else:
            self.end_media_player = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/end_video_logs.log")

        # variables
        self.file_name = file_name

        # instance methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """this method contains all the configurations related to the window"""

        self.setFixedSize(self.screen_width, self.screen_height)
        self.setCursor(Qt.BlankCursor)

    def frontend(self):
        """ this method checks for the status, if status is won then the end_media_player will play the success video
            else it will play the fail video """

        self.end_media_player.play(self.file_name)
        self.end_media_player.register_event_callback(self.verify_status_of_end_media_player)

    def verify_status_of_end_media_player(self, event):
        """this method checks if the current event emitted by the media players is end of file event, if it is then
           close the media player and the window else pass"""

        event_id = event["event_id"]
        end_of_file_id = 7

        if event_id == end_of_file_id:

            # current event id matched with end of file event id
            self.end_media_player.quit()
            self.close()

        else:
            pass


class IntroVideoWindow(QWidget):

    intro_video_ended = pyqtSignal(bool)

    def __init__(self, file_name):
        super(IntroVideoWindow, self).__init__()

        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()
        self.file_name = file_name

        # configs
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WA_NativeWindow)

        # loading mpv configurations
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as master_specs:
            config = json.load(master_specs)["mpv_configurations"]

        # widgets
        if PLATFORM == "Intel":
            self.master_intro_video_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")
        elif PLATFORM == "AMD":
            self.master_intro_video_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")
        else:
            self.master_intro_video_player = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")

        # instance methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """ this method contains the codes for the configurations of the window"""

        self.setFixedSize(self.screen_width, self.screen_height)
        self.setCursor(Qt.BlankCursor)

    def frontend(self):
        """ this method gets the intro video file, and then plays it"""

        self.master_intro_video_player.play(self.file_name)
        self.master_intro_video_player.register_event_callback(self.verify_status_of_intro_video_player)

    def verify_status_of_intro_video_player(self, event):
        """this method checks if the current event emitted by the media players is end of file event, if it is then
           close the media player and the window else pass"""

        event_id = event["event_id"]
        end_of_file_event_id = 7

        if event_id == end_of_file_event_id:

            # current event id matched with the end of file event id
            self.master_intro_video_player.quit()
            self.intro_video_ended.emit(True)
            self.close()

        else:
            pass


class NormalWindow(QMainWindow):

    def __init__(self):
        super(NormalWindow, self).__init__()

        # default variables and methods
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()
        self.restore_thread_status()

        # threads
        self.game_details_thread = threads.GameDetails()
        self.download_files_request = threads.DownloadConfigs()

        # configs
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WA_NativeWindow)

        # widgets
        self.start_threads_timer = QTimer()
        self.general_font = QFont("Ubuntu")

        # loading mpv configurations
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as master_specs:
            config = json.load(master_specs)["mpv_configurations"]

        if PLATFORM == "Intel":
            self.master_video_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")
            self.master_picture_displayer = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")

        elif PLATFORM == "AMD":
            self.master_video_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")
            self.master_picture_displayer = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")

        else:
            self.master_video_player = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")
            self.master_picture_displayer = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/intro_video_logs.log")

        self.master_image_viewer = QLabel(self)
        self.master_audio_player = mpv.MPV()

        # variables
        self.is_game_in_progress = False
        self.master_api_status = False
        self.is_master_video_playing = False
        self.is_master_audio_playing = False
        self.is_game_idle = False
        self.stop_game_response_received = False
        self.is_game_paused = False
        self.is_end_video_displayed = False
        self.game_details_api_running = False
        self.are_master_background_players_stopped = False
        self.is_application_timer_stopped = False
        self.are_threads_stopped = False
        self.are_animated_images_triggered = False
        self.is_intro_video_playing = False
        self.is_paused_game_response_received = False
        self.is_resume_game_response_received = False

        # opening unique code json file and declaring api variables
        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary_of_unique_code = json.load(unique_code_json_file)

        self.device_id = initial_dictionary_of_unique_code["Device Unique Code"]
        self.api_key = initial_dictionary_of_unique_code["apiKey"]

        self.game_details_api = "https://deviceapi.cluemaster.io/api/Device/GetGameDetails/{}".format(self.device_id)
        self.get_timer_request_api = "https://deviceapi.cluemaster.io/api/Device/GetTimerRequest/{}".format(self.device_id)

        # api headers
        self.headers = CaseInsensitiveDict()
        self.headers["Authorization"] = f"Basic {self.device_id}:{self.api_key}"

        # instance methods
        self.showFullScreen()
        self.window_configurations()
        self.frontend()

    def restore_thread_status(self):
        """ this methods restores the status of threads"""

        thread_info_dictionary = {"IsGameDetailsThreadRunning": True, "IsIdentifyDeviceThreadRunning": True,
                                  "IsGameClueThreadRunning": True, "IsTimerRequestThreadRunning": True,
                                  "IsDownloadConfigsThreadRunning": True, "IsUpdateRoomInfoThreadRunning": True,
                                  "IsShutdownRestartRequestThreadRunning": True}

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
            json.dump(thread_info_dictionary, thread_file)

    def window_configurations(self):
        """ this method contains the codes for the configuration of the window"""

        self.setFixedSize(self.screen_width, self.screen_height)
        self.setCursor(Qt.BlankCursor)

        self.full_screen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.full_screen_shortcut.activated.connect(self.go_full_screen)

        self.general_font.setWordSpacing(2)
        self.general_font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        self.setStyleSheet("background-color:transparent;")

    def go_full_screen(self):
        """ this method checks if the F11 key is pressed, if yes then check if the window is in full screen mode, if
            yes then put it back to normal else show full screen"""

        if self.isFullScreen() is True:
            # window is in full game screen mode
            self.showMaximized()
            self.setCursor(Qt.ArrowCursor)

        else:
            # window is in normal screen mode
            self.setCursor(Qt.BlankCursor)
            self.showFullScreen()

    def frontend(self):
        """ this method is triggered as soon as the NormalWindow opens and then open the GameIdle window and then
            sets the a timer of 2 seconds after timeout it triggers the start_master_threads method"""

        self.is_game_idle = True
        self.game_details_thread.app_is_idle = True
        self.external_game_idle_window = game_idle.GameIdle()
        self.external_game_idle_window.setParent(self)
        self.external_game_idle_window.show()

        self.start_threads_timer.setInterval(2000)
        self.start_threads_timer.timeout.connect(self.start_master_threads)
        self.start_threads_timer.start()

    def start_master_threads(self):
        """ this method stops the timer started in the frontend method, and then starts the master thread i.e the
            game details api"""

        self.start_threads_timer.stop()
        
        self.game_details_thread.start()
        self.game_details_thread.deviceIDcorrupted.connect(self.force_authenticate_device)
        self.game_details_thread.apiStatus.connect(self.verify_status_of_game_details_api)
        self.game_details_thread.update_detected.connect(self.restart_device)
        self.game_details_thread.statusUpdated.connect(self.verify_game_status)

        self.download_files_request.start()
        self.download_files_request.downloadFiles.connect(self.download_files)
        self.download_files_request.update_detected.connect(self.restart_device)

    def download_files(self):
        """ this method is triggered as soon as the application receives the request to download new or updated files"""

        if self.external_game_idle_window.mpv_player_triggered:
            self.external_game_idle_window.external_master_mpv_players.master_animated_image_player.terminate()
            self.external_game_idle_window.external_master_mpv_players.close()
        else:
            pass

        self.external_game_idle_window.stop_threads()
        self.external_game_idle_window.close()
        self.game_details_thread.stop()

        self.close()

        import loading_screen
        self.external_loading_window = loading_screen.LoadingScreen()

    def verify_game_status(self, game_status):
        """ this method is called every 4 to 5 seconds to verify latest game status"""

        if game_status == 1:
            # if status is 1 then start or resume game

            self.resume_game()

            if self.is_game_in_progress is False:
                self.is_game_in_progress = True
                self.game_details_thread.app_is_idle = False
                self.download_files_request.stop()
                self.load_intro_video()

            else:
                pass

        elif game_status == 2:
            # if status is 2 then stop game

            if self.is_game_in_progress is True:
                if self.stop_game_response_received is False:
                    self.stop_game_response_received = True
                    self.is_game_in_progress = False
                    self.stop_game()
                else:
                    pass
            else:
                pass

        elif game_status == 3:
            # if status is 3 then reset game

            if self.is_game_idle is False:

                if self.is_intro_video_playing is True:
                    self.game_details_thread.stop()
                    self.external_game_idle_window.stop_threads()

                    try:
                        self.external_network_status_window.close()
                    except AttributeError:
                        pass

                    self.external_intro_video_window.master_intro_video_player.unregister_event_callback(self.external_intro_video_window.verify_status_of_intro_video_player)
                    self.external_intro_video_window.master_intro_video_player.terminate()
                    self.external_intro_video_window.close()

                    time.sleep(10)

                    if self.external_game_idle_window.mpv_player_triggered:
                        self.external_game_idle_window.external_master_mpv_players.master_animated_image_player.terminate()
                        self.external_game_idle_window.external_master_mpv_players.close()
                    else:
                        pass

                    self.deleteLater()
                    self.external_game_idle_window.close()
                    self.normal_window = NormalWindow()

                else:
                    self.game_details_thread.stop()

                    if self.are_threads_stopped is False:

                        self.external_master_overlay_window.timer_request_thread.stop()
                        self.external_clue_containers_window.get_game_clue_thread.stop()
                        self.external_clue_containers_window.hide_clue_containers()
                        self.external_clue_containers_window.close()

                        try:
                            self.external_network_status_window.close()
                        except AttributeError:
                            pass

                    else:
                        pass

                    if self.are_master_background_players_stopped is False:
                        if self.is_master_audio_playing is True:
                            self.master_video_player._set_property("pause", True)

                        if self.is_master_audio_playing is True:
                            self.master_audio_player.stop()
                            self.master_audio_player.quit()

                        if self.are_animated_images_triggered is True:
                            self.master_picture_displayer._set_property("pause", True)

                    else:
                        pass

                    if self.is_application_timer_stopped is False:

                        if self.external_master_overlay_window.is_countup_timer_active is True:
                            self.external_master_overlay_window.countup_timer.stop()

                        elif self.external_master_overlay_window.is_countdown_timer_active is True:
                            self.external_master_overlay_window.countdown_timer.stop()

                    else:
                        pass

                    try:
                        # self.custom_end_media_widget.end_media_player.stop()
                        self.custom_end_media_widget.end_media_player.unregister_event_callback(self.custom_end_media_widget.verify_status_of_end_media_player)
                        self.custom_end_media_widget.end_media_player.terminate()
                        self.custom_end_media_widget.close()

                    except AttributeError:
                        pass

                    try:
                        # self.custom_end_audio_media_widget.master_audio_player.stop()
                        self.custom_end_audio_media_widget.master_audio_player.unregister_event_callback(self.custom_end_audio_media_widget.verify_status_of_master_audio_player)
                        self.custom_end_audio_media_widget.master_audio_player.terminate()
                        self.custom_end_audio_media_widget.close()

                    except AttributeError:
                        pass

                    time.sleep(10)

                    self.external_clue_icon_container_window.close()
                    self.external_master_overlay_window.close()
                    self.close()

                    self.normal_window = NormalWindow()
                    self.normal_window.showFullScreen()

        elif game_status == 4:
            # if status is 4 then pause game

            if self.is_game_in_progress is True:
                self.pause_game()

            else:
                pass

    def trigger_update_clues_used_method(self, response):
        """ this method triggers the update_clues_method in the ClueIconContainer window to update the number of
            clues used"""

        if self.is_game_in_progress:
            self.external_clue_icon_container_window.update_clues_used(used=response)
        else:
            pass

    def restart_device(self):
        """ this method is triggered as soon as the restart signal is emitted by the shutdown restart thread"""
        import dbus

        bus = dbus.SystemBus()
        bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
        bus_object.Reboot(True, dbus_interface="org.freedesktop.login1.Manager")

        self.close()

    def force_authenticate_device(self):
        """ this method is triggered if the user deletes the device from app.cluemaster.io, this method stops the
            threads and the forces the app to the authentication window """

        self.game_details_thread.stop()
        self.external_game_idle_window.stop_threads()
        self.download_files_request.stop()

        try:
            self.external_network_status_window.deleteLater()
        except AttributeError:
            pass

        time.sleep(10)

        if self.external_game_idle_window.mpv_player_triggered:
            self.external_game_idle_window.external_master_mpv_players.master_animated_image_player.terminate()
            self.external_game_idle_window.external_master_mpv_players.close()
        else:
            pass

        self.deleteLater()
        self.external_game_idle_window.deleteLater()
        self.authenticate_window = authentication_screen.AuthenticationWindow()

    def load_intro_video(self):
        """ this method stops threads like identify device thread, shutdown or restart device thread and the
            download files request thread and then checks if intro video is enabled, if yes then starts the intro video,
            else starts the game"""

        if self.external_game_idle_window.mpv_player_triggered:
            self.external_game_idle_window.external_master_mpv_players.master_animated_image_player.terminate()
            self.external_game_idle_window.external_master_mpv_players.close()
        else:
            pass

        self.external_game_idle_window.stop_threads()
        self.external_game_idle_window.close()
        self.is_game_idle = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
                initial_dictionary = json.load(game_details_json_file)

            game_details_response = initial_dictionary

            if game_details_response["isIntro"] is True:
                # intro video is enabled
                self.master_intro_video_container()

            else:
                # intro video is not enabled
                self.master_media_files()

        except json.decoder.JSONDecodeError:
            # if the method faces JSONDecodeError, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the method faces simplejson DecodeError, then pass
            pass

    def master_media_files(self):
        """ this method triggers the NetworkStatus window and the ClueContainers window and then starts the master
            or background videos or audios or displays the background picture based on a hierarchy order"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json")) as device_configurations_json_file:
            initial_dictionary = json.load(device_configurations_json_file)

        room_info_response = initial_dictionary
        self.game_details_thread.updateCluesUsed.connect(self.trigger_update_clues_used_method)

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
                initial_dictionary_of_game_details = json.load(game_details_json_file)

            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json")) as device_configurations_json_file:
                initial_dictionary_of_room_info = json.load(device_configurations_json_file)

            game_details_response = initial_dictionary_of_game_details
            room_info_response = initial_dictionary_of_room_info

            if game_details_response["isVideo"] is True:
                # background or master video is enabled
                self.master_background_video_container()

                if game_details_response["isMusic"] is True:
                    # background or master audio is enabled
                    self.master_background_audio_container()

            elif game_details_response["isMusic"] is True:
                # background or master audio is enabled
                self.master_background_audio_container()

                if room_info_response["IsPhoto"] is True:
                    # background or master image is enabled
                    self.master_background_image_container()

            elif room_info_response["IsPhoto"] is True:
                # master or background image is enabled
                self.master_background_image_container()

            else:
                # if no master video or audio or image is enabled, show dark blue window
                self.setStyleSheet("background-color: #191F26;")

        except json.decoder.JSONDecodeError:
            # if the method faces JSONDecodeError, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the method faces simplejson DecodeError, then pass
            pass

        # classes
        self.external_master_overlay_window = master_overlay.MasterOverlay()
        self.external_master_overlay_window.game_ended.connect(self.processing_stop_game_request_from_timers)

        if room_info_response["Clues Allowed"] is True:
            self.external_clue_icon_container_window = master_overlay.ClueContainer()
            self.external_clue_icon_container_window.showFullScreen()

        else:
            pass

        self.external_clue_containers_window = clue_containers.ClueWindow()
        self.external_clue_containers_window.mute_game.connect(self.mute_game)
        self.external_clue_containers_window.unmute_game.connect(self.unmute_game)

    def master_intro_video_container(self):
        """ this method is triggered as soon as the game starts, this method checks if the intro video is already
            played, if yes then starts the main game screen else starts the intro video player"""

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
                initial_dictionary = json.load(game_details_json_file)

            game_details_response = initial_dictionary
            game_id = game_details_response["gameId"]

            get_intro_request_api = "https://deviceapi.cluemaster.io/api/Device/GetGameIntroRequest/{}".format(game_id)
            get_intro_api_response = requests.get(get_intro_request_api, headers=self.headers).content.decode("utf-8")

            if get_intro_api_response != "No record found":
                # intro video is not shown to the users till now

                default = os.path.join(MASTER_DIRECTORY, "assets/room data/intro media/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/intro media/"))[0]))

                self.is_intro_video_playing = True
                self.external_intro_video_window = IntroVideoWindow(file_name=default)
                self.external_intro_video_window.setParent(self)
                self.external_intro_video_window.showFullScreen()
                self.external_intro_video_window.intro_video_ended.connect(self.verify_status_of_intro_video_window)

            else:
                # intro video have been already displayed, so starting main game screen
                self.master_media_files()

        except requests.exceptions.ConnectionError:
            # if the method faces connection error, then pass
            pass

        except json.decoder.JSONDecodeError:
            # if the method faces JSONDecodeError, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the method faces simplejson DecodeError, then pass
            pass

    def verify_status_of_intro_video_window(self):
        """ ths method is called as soon as the intro video player ends, codes are programmed to wait until the app
            receives the update timer request from from the webapp, and then it moves to the main game screen """

        print("Verify ending of Intro Video")

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
                initial_dictionary = json.load(game_details_json_file)

            game_details_response = initial_dictionary
            if game_details_response["gameStatus"] != 3:

                self.is_intro_video_playing = False
                self.intro_post_request()

                self.check_timer_request_thread = CheckTimerRequestThread()
                self.check_timer_request_thread.start()
                self.check_timer_request_thread.proceed.connect(self.master_media_files)

        except json.decoder.JSONDecodeError:
            # if the method faces JSONDecodeError, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the method faces simplejson DecodeError, then pass
            pass

    def intro_post_request(self):
        """ this method is triggered from the method verify_status_of_intro_video_window and this method sends a post
            response to the webapp saying that the intro video ended in the app """

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
                initial_dictionary = json.load(game_details_json_file)

            game_details_response = initial_dictionary
            game_id = game_details_response["gameId"]

            get_intro_request_api = "https://deviceapi.cluemaster.io/api/Device/GetGameIntroRequest/{}".format(game_id)
            response_of_intro_request_api = requests.get(get_intro_request_api, headers=self.headers).json()
            device_request_id = response_of_intro_request_api["DeviceRequestid"]
            requests.post("https://deviceapi.cluemaster.io/api/Device/{}/{}".format(self.device_id, device_request_id), headers=self.headers)

        except requests.exceptions.ConnectionError:
            # if the method faces connection error, then pass
            pass

        except json.decoder.JSONDecodeError:
            # if the method faces JSONDecodeError, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the method faces simplejson DecodeError, then pass
            pass

    def master_background_video_container(self):
        """ this method holds the location of the master or background video and loads it into the master_video_player
            and then starts playing it"""

        try:
            default = os.path.join(MASTER_DIRECTORY, "assets/room data/video/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/video/"))[0]))
        except IndexError:
            print(">>> Console output - Master background video not found")
        except FileNotFoundError:
            print(">>> Console output - Master background video not found")
        else:
            if os.path.isfile(default):
                self.master_video_player.loop = True
                self.master_video_player.play(default)
                self.is_master_video_playing = True
            else:
                pass

    def master_background_image_container(self):
        """ this method holds the location of the master or background photo and loads it into a QLabel and
            displays it"""

        try:
            default = os.path.join(MASTER_DIRECTORY, "assets/room data/picture/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/picture/"))[0]))
        except IndexError:
            print(">>> Console output - Master background image not found")
        except FileNotFoundError:
            print(">>> Console output - Master background image not found")
        else:
            if os.path.isfile(default):
                if default.endswith(".apng") or default.endswith(".ajpg") or default.endswith(".gif"):

                    self.are_animated_images_triggered = True
                    self.master_picture_displayer.loop = True
                    self.master_picture_displayer.play(default)

                elif default.endswith(".svg"):

                    self.master_animated_svg_renderer = QSvgWidget(default)
                    self.master_animated_svg_renderer.resize(self.screen_width, self.screen_height)
                    self.master_animated_svg_renderer.setParent(self)
                    self.master_animated_svg_renderer.show()

                else:
                    self.master_image_viewer.resize(self.screen_width, self.screen_height)
                    self.master_image_viewer.setPixmap(QPixmap(default).scaled(self.screen_width, self.screen_height))
                    self.setCentralWidget(self.master_image_viewer)
                    self.master_image_viewer.show()
            else:
                pass

    def master_background_audio_container(self):
        """ this method holds the location of the master or background music and loads it into the master_audio_player
           and then starts playing it """

        try:
            default = os.path.join(MASTER_DIRECTORY, "assets/room data/music/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/music/"))[0]))
        except IndexError:
            print(">>> Console output - Background audio not found")
        except FileNotFoundError:
            print(">>> Console output - Background audio not found")
        else:
            if os.path.isfile(default):
                self.master_audio_player.play(default)
                self.master_audio_player.loop = True
                self.is_master_audio_playing = True
            else:
                pass

    def pause_game(self):
        """ this method pauses the videos, audios and the timers"""

        if self.is_paused_game_response_received is False:

            if self.is_master_video_playing:
                # master or background video is playing
                self.master_video_player._set_property("pause", True)

            if self.is_master_audio_playing:
                # master or background audio is playing
                self.master_audio_player._set_property("pause", True)

            if self.external_master_overlay_window.is_countup_timer_active is True:
                # countup timer is active
                self.external_master_overlay_window.countup_timer.stop()

            elif self.external_master_overlay_window.is_countdown_timer_active is True:
                # countdown timer is active
                self.external_master_overlay_window.countdown_timer.stop()

            self.is_paused_game_response_received = True
            self.is_game_paused = True
            self.is_resume_game_response_received = False

        else:
            pass

    def resume_game(self):
        """ this method resumes the paused videos, audios and the timers"""

        if self.is_game_paused is True:
            if self.is_resume_game_response_received is False:
                self.is_game_idle = False

                if self.is_master_video_playing:
                    # master or background video is paused, resuming it
                    self.master_video_player._set_property("pause", False)

                if self.is_master_audio_playing:
                    # master or background audio is paused, resuming it
                    self.master_audio_player._set_property("pause", False)

                if self.external_master_overlay_window.is_countup_timer_active is True:
                    # countup timer is paused, starting it
                    self.external_master_overlay_window.countup_timer.start()

                elif self.external_master_overlay_window.is_countdown_timer_active is True:
                    # countdown timer is paused, starting it
                    self.external_master_overlay_window.countdown_timer.start()

                self.is_resume_game_response_received = True
                self.is_paused_game_response_received = False

            else:
                pass
        else:
            pass

    def processing_stop_game_request_from_timers(self):
        """ this method is triggered as soon as the game_ended signal is emitted by the MasterOverlay window.
            the gam_ended signal is emitted once countdown timer hits 0"""

        if self.stop_game_response_received is False:
            self.stop_game_response_received = True
            self.stop_game()
        else:
            pass

    def mute_game(self, default):
        """ this method is triggered when the mute signal is emitted by the ClueContainers window, the mute signal
             is usually emitted if video or audio clue starts playing"""

        if default:
            # if audio clue is playing

            if self.is_master_video_playing is True:
                # master or background video is playing, muting it
                self.master_video_player._set_property("mute", True)

            if self.is_master_audio_playing is True:
                # master or background audio is playing, muting it
                self.master_audio_player._set_property("mute", True)
        else:
            # if video clue is playing

            if self.is_master_video_playing is True:
                # master or background video is playing, pausing it
                self.master_video_player._set_property("pause", True)

            if self.is_master_audio_playing is True:
                # master or background audio is playing, pausing it
                self.master_audio_player._set_property("pause", True)

    def unmute_game(self, default):
        """ this method is triggered when the unmute signal is emitted by the ClueContainers window, the unmute signal
            is usually emitted if video or audio clue stops playing"""

        if default is True:
            # if audio clue is playing

            if self.is_master_video_playing is True:
                # master or background video is muted, unmuting it
                self.master_video_player._set_property("mute", False)

            if self.is_master_audio_playing is True:
                # master or background audio is muted, unmuting it
                self.master_audio_player._set_property("mute", False)
        else:
            # if video clue is playing

            if self.is_master_video_playing is True:
                # master or background video is paused, resuming it
                self.master_video_player._set_property("pause", False)

            if self.is_master_audio_playing is True:
                # master or background audio is paused, resuming it
                self.master_audio_player._set_property("pause", False)

    def stop_game(self):
        """ this method is triggered either from the processing_stop_request_from_timers or when the game status is 2,
            this method stops the whole game and prepares to reset the it and start a new one"""

        # stop threads

        self.external_master_overlay_window.timer_request_thread.stop()
        self.external_clue_containers_window.get_game_clue_thread.stop()
        self.external_clue_containers_window.hide_clue_containers()
        self.external_clue_containers_window.close()

        try:
            self.external_network_status_window.close()
        except AttributeError:
            pass

        self.are_threads_stopped = True

        if self.is_master_video_playing is True:
            self.master_video_player._set_property("pause", True)

        if self.is_master_audio_playing is True:
            self.master_audio_player.stop()
            self.master_audio_player.quit()

        if self.are_animated_images_triggered is True:
            self.master_picture_displayer._set_property("pause", True)

        self.are_master_background_players_stopped = True

        # stop/pause application countdown timers
        if self.external_master_overlay_window.is_countup_timer_active is True:
            self.external_master_overlay_window.countup_timer.stop()

        elif self.external_master_overlay_window.is_countdown_timer_active is True:
            self.external_master_overlay_window.countdown_timer.stop()

        self.is_application_timer_stopped = True

        try:
            game_details_response = requests.get(self.game_details_api, headers=self.headers).json()
            win_loss_text = game_details_response["winLossText"]

            if win_loss_text == "won":
                self.master_end_media_container(status="won")

            elif win_loss_text == "lost":
                self.master_end_media_container(status="lost")

            elif self.external_master_overlay_window.is_countup_timer_active is True:
                self.master_end_media_container(status="won")

            elif self.external_master_overlay_window.is_countdown_timer_active is True:
                self.master_end_media_container(status="lost")

            else:
                self.master_end_media_container(status="lost")

        except requests.exceptions.ConnectionError:
            # if the method faces connection error, then pass
            pass

        except json.decoder.JSONDecodeError:
            # if the method faces JSONDecodeError, then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the method faces simplejson DecodeError, then pass
            pass

    def master_end_media_container(self, status):
        """ this method starts the EndMediaWidget widow and show the end media that is either win video or lost video"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json")) as device_configurations_json_file:
            initial_dictionary = json.load(device_configurations_json_file)

        room_info_response = initial_dictionary

        if status == "won":
            if room_info_response["IsSuccessVideo"] is True:  # checking if the win video is enabled in the webapp
                default = os.path.join(MASTER_DIRECTORY, "assets/room data/success end media/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/success end media/"))[0]))

                if default.endswith(".mp3") or default.endswith(".wav"):
                    self.custom_end_audio_media_widget = EndAudioMediaWidget(file_name=default)
                else:
                    self.custom_end_media_widget = EndMediaWidget(file_name=default)
                    self.custom_end_media_widget.showFullScreen()
            else:
                pass

        elif status == "lost":
            if room_info_response["IsFailVideo"] is True:  # checking if the lost video is enabled in the webapp
                default = os.path.join(MASTER_DIRECTORY, "assets/room data/fail end media/{}".format(os.listdir(os.path.join(MASTER_DIRECTORY, "assets/room data/fail end media"))[0]))

                if default.endswith(".mp3") or default.endswith(".wav"):
                    self.custom_end_audio_media_widget = EndAudioMediaWidget(file_name=default)
                else:
                    self.custom_end_media_widget = EndMediaWidget(file_name=default)
                    self.custom_end_media_widget.showFullScreen()
            else:
                pass

        self.is_end_video_displayed = True

    def verify_status_of_game_details_api(self, status):
        """ this method is called as soon as the apiStatus signal of game details thread is emitted"""

        if status == 1:
            #  thread is working fine
            self.game_details_api_running = True
            self.update_application_network_status()

        else:
            # thread is facing issues
            self.game_details_api_running = False
            self.update_application_network_status()

    def update_application_network_status(self):
        """ this method checks if any apis are down or facing errors retrieving data from the web, if yes then
            show the red border around the game window else pass"""

        if self.game_details_api_running:
            # one or more apis are working fine
            try:
                if self.master_api_status is True:
                    pass
                else:
                    print(">>> Console output - Master api is up and running")
                    self.master_api_status = True
                    self.external_network_status_window.close()
            except AttributeError:
                pass

        elif not self.game_details_api_running:
            # one or more apis are facing issues, deploying red border
            try:
                if self.master_api_status is False:
                    pass
                else:
                    print(">>> Console output - Master api is down, red bars")
                    self.master_api_status = False
                    self.external_network_status_window = NetworkStatus()
                    self.external_network_status_window.frontend()
            except AttributeError:
                pass

        else:
            pass
