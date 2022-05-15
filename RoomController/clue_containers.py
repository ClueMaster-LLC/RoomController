import time
import os
import requests
import simplejson.errors
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import threads
import json
import mpv
from requests.structures import CaseInsensitiveDict

# Setting up base directories
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterDisplay")

# Pulling up platform specifications
with open(os.path.join(MASTER_DIRECTORY, "assets/application data/platform_specs.json")) as platform_specs_file:
    PLATFORM = json.load(platform_specs_file)["platform"]


class TextClueContainer(QWidget):

    def __init__(self, text, preferred_height):
        super(TextClueContainer, self).__init__()

        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()
        self.preferred_height = preferred_height

        # widgets
        self.text_clue_container = QLabel(self)

        # variables
        self.text = text

        #  instance methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """ this method contains code for the configurations of the window """

        self.move(0, self.screen_height - self.preferred_height)
        self.setStyleSheet("background-color: black;")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setCursor(Qt.BlankCursor)

    def frontend(self):
        """ this method contains the codes for showing the text clue labels"""

        self.text_clue_container.setFixedSize(self.screen_width, int(self.preferred_height))
        self.text_clue_container.setFont(QFont("Ubuntu", int(self.screen_height / 24.41)))
        self.text_clue_container.setText(self.text)
        self.text_clue_container.setWordWrap(True)
        self.text_clue_container.setAlignment(Qt.AlignCenter | Qt.AlignHCenter)
        self.text_clue_container.setStyleSheet("color:white; font-weight:bold; background-color:rgba(17, 17, 17, 0.7);")

        self.regional_box_layout = QVBoxLayout(self)
        self.regional_box_layout.addWidget(self.text_clue_container, alignment=Qt.AlignCenter | Qt.AlignBottom)
        self.text_clue_container.show()


class ClueVideoWidget(QWidget):

    clue_video_ended = pyqtSignal()

    def __init__(self, file_name):
        super(ClueVideoWidget, self).__init__()

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

        # widget

        if PLATFORM == "Intel":
            self.master_clue_video_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/clue_video_player_logs.log")
        elif PLATFORM == "AMD":
            self.master_clue_video_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/clue_video_player_logs.log")
        else:
            self.master_clue_video_player = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/clue_video_player_logs.log")

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

        self.master_clue_video_player.play(self.file_name)
        self.master_clue_video_player.register_event_callback(self.verify_status_of_master_clue_video_player)

    def force_quit(self):
        """this method force quit the player and the window"""

        try:
            self.master_clue_video_player.quit()
            self.close()

        except RuntimeError:
            pass

    def verify_status_of_master_clue_video_player(self, event):
        """ this method is triggered with every event emitted by the media player"""

        current_event_id = event["event_id"]
        end_of_file_event_id = 7

        if current_event_id == end_of_file_event_id:
            # if the current media player event matches with the end of file event id then emit the clue_video_ended
            # signal and then close the window
            try:
                self.master_clue_video_player.quit()
                self.clue_video_ended.emit()
                self.close()

            except RuntimeError:
                pass
        else:
            pass


class ClueAnimatedImageContainer(QWidget):

    def __init__(self, file_name):
        super(ClueAnimatedImageContainer, self).__init__()

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

        # widget
        if PLATFORM == "Intel":
            self.master_animated_image_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/clue_image_player_logs.log")
        elif PLATFORM == "AMD":
            self.master_animated_image_player = mpv.MPV(wid=str(int(self.winId())), hwdec=config["hwdec"], vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/clue_image_player_logs.log")
        else:
            self.master_animated_image_player = mpv.MPV(wid=str(int(self.winId())), vo=config["vo"], log_file=f"{MASTER_DIRECTORY}/clue_image_player_logs.log")

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


class ClueAnimatedSVGRenderer(QWidget):

    def __init__(self, file_name):
        super(ClueAnimatedSVGRenderer, self).__init__()

        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

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

        self.master_svg_renderer = QSvgWidget(self.file_name)
        self.master_svg_renderer.resize(self.screen_width, self.screen_height)
        self.master_svg_renderer.setParent(self)
        self.master_svg_renderer.show()


class AudioClueContainer(QWidget):

    audio_ended = pyqtSignal()

    def __init__(self, file_name):
        super(AudioClueContainer, self).__init__()

        # widgets
        self.master_audio_player = mpv.MPV()

        # variables
        self.file = file_name

        # methods
        self.window_configurations()
        self.frontend()

    def window_configurations(self):
        """ this method contains code for the configurations of the window"""

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
                self.audio_ended.emit()
                self.close()

            except RuntimeError:
                pass
        else:
            pass


class ClueWindow(QWidget):

    mute_game = pyqtSignal(bool)
    unmute_game = pyqtSignal(bool)

    def __init__(self):
        super(ClueWindow, self).__init__()

        # default variables
        self.screen_width = QApplication.desktop().width()
        self.screen_height = QApplication.desktop().height()

        # threads
        self.get_game_clue_thread = threads.GetGameClue()
        self.get_game_clue_thread.start()
        self.get_game_clue_thread.statusChanged.connect(self.frontend)
        self.get_game_clue_thread.update_detected.connect(self.restart_device)

        # widgets
        self.master_layout = QVBoxLayout(self)
        self.text_clue_container = QLabel(self)
        self.notify_audio_player = mpv.MPV()

        self.image_clue_container = QLabel(self)

        # variables
        self.preferred_height = self.screen_height / 2.6
        self.is_master_video_clue_playing = False
        self.is_master_audio_clue_playing = False
        self.is_text_clue_visible = False
        self.is_image_clue_visible = False
        self.is_animated_image_clue_playing = False
        self.is_svg_clue_visible = False

        # headers

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary

        self.device_id = unique_code_response["Device Unique Code"]
        self.api_key = unique_code_response["apiKey"]

        self.headers = CaseInsensitiveDict()
        self.headers["Authorization"] = f"Basic {self.device_id}:{self.api_key}"

        # instance methods
        self.window_configurations()

    def window_configurations(self):
        """ this method contains code for the configurations of the window"""

        self.resize(self.screen_width, self.screen_height)
        self.move(0, 0)
        self.setCursor(Qt.BlankCursor)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setAttribute(Qt.WA_NoSystemBackground)

        self.hide()

    def frontend(self):
        """ this method contains the codes for determining the type of clue and calling the respective method"""

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameClue.json")) as game_clue_json_file:
                initial_dictionary = json.load(game_clue_json_file)

            game_clue_response = initial_dictionary

            if game_clue_response["clueStatus"] is True:

                self.hide_clue_containers()

                if game_clue_response["clueType"] == "TextClue":
                    # if the clue type is text then call the master_text_clue_container
                    self.master_text_clue_container(text=game_clue_response["clueText"])

                elif game_clue_response["clueType"] == "Message":
                    # if the clue type is message then call the master_text_clue_container
                    self.master_text_clue_container(text=game_clue_response["clueText"])

                elif game_clue_response["clueFilename"].split("/")[0] == "video":
                    # if the clue falls under video category then call the master_video_clue_container
                    self.master_video_clue_container(file_name=game_clue_response["clueFilename"].split("/")[1])

                elif game_clue_response["clueFilename"].split("/")[0] == "audio":
                    # if the clue falls under audio then call the master_audio_clue_container
                    self.master_audio_clue_container(file_name=game_clue_response["clueFilename"].split("/")[1])

                elif game_clue_response["clueFilename"].split("/")[0] == "photo":
                    # if the clue falls under the photo category then calls the master_image_clue_container
                    self.master_image_clue_container(file_name=game_clue_response["clueFilename"].split("/")[1])

                else:
                    pass

            else:
                self.hide_clue_containers()

        except json.decoder.JSONDecodeError:
            # if the code inside the try block faces json decode error then pass
            pass

        except simplejson.errors.JSONDecodeError:
            # if the code inside the try block faces simplejson decode error, then pass
            pass

        except AttributeError:
            pass

    def restart_device(self):
        """ this method is triggered as soon as the restart signal is emitted by the shutdown restart thread"""
        import dbus

        bus = dbus.SystemBus()
        bus_object = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
        bus_object.Reboot(True, dbus_interface="org.freedesktop.login1.Manager")

        self.close()

    def master_text_clue_container(self, text):
        """ this method when called plays the alert audio and then opens the TextClueContainer window for showing the
            text clue or the manual typed message"""

        self.is_text_clue_visible = True
        self.notify_audio_player.play(os.path.join(ROOT_DIRECTORY, "assets/MessageAlert.mp3"))

        self.external_text_clue_container_window = TextClueContainer(text=text, preferred_height=self.preferred_height)
        self.external_text_clue_container_window.showFullScreen()

    def master_video_clue_container(self, file_name):
        """ this method when called emits a mute signal and then opens the ClueVideoWidget window for
            showing the video clue"""

        default = os.path.join(MASTER_DIRECTORY, "assets/clue medias/" + file_name)

        if os.path.isfile(default):
            self.mute_game.emit(False)
            self.is_master_video_clue_playing = True

            self.external_clue_video_window = ClueVideoWidget(file_name=default)
            self.external_clue_video_window.setParent(self)
            self.external_clue_video_window.clue_video_ended.connect(self.master_clue_video_player_ended)
            self.external_clue_video_window.showFullScreen()
            self.showFullScreen()
        else:
            print(">>> Console output - Clue video not found")

    def master_clue_video_player_ended(self):
        """ this method is triggered when the clue_video_ended signal is emitted by the ClueVideoWidget window"""

        self.hide()
        self.send_game_clue_status_response()
        self.unmute_game.emit(False)
        self.is_master_video_clue_playing = False

    def master_audio_clue_container(self, file_name):
        """ this method when called emits a mute signal and then opens the AudioClueContainer window for
            playing the audio clue"""

        default = os.path.join(MASTER_DIRECTORY, "assets/clue medias/" + file_name)
        if os.path.isfile(default):

            self.mute_game.emit(True)
            self.is_master_audio_clue_playing = True

            self.external_audio_clue_container_window = AudioClueContainer(file_name=default)
            self.external_audio_clue_container_window.audio_ended.connect(self.master_clue_audio_player_ended)
        else:
            print(">>> Console output - Audio clue not found")

    def master_clue_audio_player_ended(self):
        """ this method is triggered when the audio_ended signal is emitted by the AudioClueContainer window"""

        self.send_game_clue_status_response()
        self.unmute_game.emit(True)
        self.is_master_audio_clue_playing = False

    def master_image_clue_container(self, file_name):
        """ this method when triggered shows or displays the image clue """

        default = os.path.join(MASTER_DIRECTORY, "assets/clue medias/" + file_name)

        if os.path.isfile(default):
            if default.endswith(".gif") or default.endswith(".apng") or default.endswith(".ajpg") or default.endswith(".jpg") or default.endswith(".PNG") or default.endswith(".jpeg") or default.endswith(".png") or default.endswith(".JPG"):

                self.is_animated_image_clue_playing = True
                self.notify_audio_player.play(os.path.join(ROOT_DIRECTORY, "assets/MessageAlert.mp3"))
                self.external_clue_gif_window = ClueAnimatedImageContainer(file_name=default)
                self.external_clue_gif_window.setParent(self)
                self.external_clue_gif_window.showFullScreen()
                self.showFullScreen()

            elif default.endswith(".svg"):

                self.is_svg_clue_visible = True
                self.notify_audio_player.play(os.path.join(ROOT_DIRECTORY, "assets/MessageAlert.mp3"))
                self.external_clue_animated_svg_renderer = ClueAnimatedSVGRenderer(file_name=default)
                self.external_clue_animated_svg_renderer.setParent(self)
                self.external_clue_animated_svg_renderer.showFullScreen()
                self.showFullScreen()
        else:
            print(">>> Console output - No clue image found")

    def hide_clue_containers(self):
        """ this method when called, closes every opened windows and emits the unmute signal if required"""
        print(""">>> Console output - Hide clue containers method""")
        self.hide()

        if self.is_master_video_clue_playing is True:
            self.external_clue_video_window.master_clue_video_player.unregister_event_callback(self.external_clue_video_window.verify_status_of_master_clue_video_player)
            self.external_clue_video_window.master_clue_video_player.terminate()
            self.external_clue_video_window.close()
            self.unmute_game.emit(False)
            self.is_master_video_clue_playing = False

        elif self.is_master_audio_clue_playing is True:
            self.external_audio_clue_container_window.master_audio_player.unregister_event_callback(self.external_audio_clue_container_window.verify_status_of_master_audio_player)
            self.external_audio_clue_container_window.master_audio_player.terminate()
            self.external_audio_clue_container_window.close()
            self.unmute_game.emit(True)
            self.is_master_audio_clue_playing = False

        elif self.is_text_clue_visible is True:
            self.external_text_clue_container_window.close()
            self.is_text_clue_visible = False

        elif self.is_animated_image_clue_playing is True:
            self.external_clue_gif_window.master_animated_image_player.terminate()
            self.external_clue_gif_window.close()
            self.is_animated_image_clue_playing = False

        elif self.is_svg_clue_visible is True:
            self.external_clue_animated_svg_renderer.close()
            self.is_svg_clue_visible = False

    def send_game_clue_status_response(self):
        """ this method sends a post response, when the video or audio clue finishes playing, to notify the webapp to
            restore the clue status"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameClue.json")) as game_clue_json_file:
            initial_dictionary = json.load(game_clue_json_file)

        game_clue_response = initial_dictionary
        game_id = game_clue_response["gameId"]
        clue_id = game_clue_response["gameClueId"]

        post_game_status_api = "https://deviceapi.cluemaster.io/api/Device/PostGameClueStatus/{game_ids}/{clue_ids}"

        while True:
            try:
                post_request = requests.post(post_game_status_api.format(game_ids=game_id, clue_ids=clue_id), headers=self.headers)

            except requests.exceptions.ConnectionError:
                # if the post response inside the try block faces connection error while making the response then
                # wait 2 seconds before retrying
                time.sleep(2)

            else:
                break
