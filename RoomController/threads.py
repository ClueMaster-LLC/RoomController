import json
import time
import requests
import simplejson
from requests.structures import CaseInsensitiveDict
from PyQt5.QtCore import QThread, pyqtSignal
import os

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterDisplay")


class GameDetails(QThread):

    # signals
    statusUpdated = pyqtSignal(int)
    updateCluesUsed = pyqtSignal(int)
    apiStatus = pyqtSignal(int)
    deviceIDcorrupted = pyqtSignal()
    update_detected = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""
        self.app_is_idle = True

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        device_unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {device_unique_code}:{api_key}"

        game_details_url = f"https://deviceapi.cluemaster.io/api/Device/GetGameDetails/{device_unique_code}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsGameDetailsThreadRunning"] is True:
                    pass
                else:
                    return

                print(">>> Console output - Game Details")
                response = requests.get(game_details_url, headers=headers)
                print(">>> Console output - Is App Idle - ", self.app_is_idle)

                if self.app_is_idle is True and response.status_code == 401:
                    print(">>> Console output - Device Corrupted...")
                    self.deviceIDcorrupted.emit()

                elif response.status_code != 200:
                    print(">>> Console output - API Response not 200")
                    pass
                else:
                    response = response.json()
                    game_status = response["gameStatus"]
                    clue_used = response["noOfCluesUsed"]

                    if clue_used is None:
                        pass
                    else:
                        self.updateCluesUsed.emit(clue_used)

                    with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json"), "w") as game_details_json_file:
                        json.dump(response, game_details_json_file)

                    self.statusUpdated.emit(game_status)

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls then pass
                self.apiStatus.emit(0)

            except json.decoder.JSONDecodeError:
                # if the codes inside the try block faces json decode error then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the codes inside the try block faces simplejson decode error then pass
                pass

            except PermissionError:
                # application update detected
                self.update_detected.emit()

            else:
                # if no error then
                self.apiStatus.emit(1)

            finally:
                # and finally
                time.sleep(5)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsGameDetailsThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.update_detected.emit()


class IdentifyDevice(QThread):

    # signals
    identify_device = pyqtSignal(int)
    update_detected = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        device_unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {device_unique_code}:{api_key}"

        identify_device_url = f"https://deviceapi.cluemaster.io/api/Device/IdentifyDevice/{device_unique_code}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsIdentifyDeviceThreadRunning"] is True:
                    pass

                else:
                    return

                print(">>> Console output - Identify device")
                json_response = requests.get(identify_device_url, headers=headers).json()

                display_text = json_response["DisplayText"]
                request_date = json_response["Requestdate"]

                dictionary = {"DisplayText": display_text, "Requestdate": request_date}

                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/IdentifyDeviceDetails.json"), "w") as identify_device_details_json_file:
                    json.dump(dictionary, identify_device_details_json_file)

                self.identify_device.emit(1)

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls, then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the code inside the try is facing json decode error then pass
                self.identify_device.emit(0)

            except simplejson.errors.JSONDecodeError:
                # if the code inside the try is facing simplejson decode error then pass
                self.identify_device.emit(0)

            except FileNotFoundError:
                # if the code faces the FilNotFoundError then pass
                pass

            except PermissionError:
                # application update detected
                self.update_detected.emit()

            finally:
                # and finally
                time.sleep(15)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsIdentifyDeviceThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.update_detected.emit()


class ShutdownRestartRequest(QThread):

    # signals
    shutdown = pyqtSignal()
    restart = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {unique_code}:{api_key}"

        shutdown_restart_api = f"https://deviceapi.cluemaster.io/api/Device/GetShutdownRestartRequest/{unique_code}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsShutdownRestartRequestThreadRunning"] is True:
                    pass

                else:
                    return

                print(">>> Console output - Shutdown restart response")
                json_response = requests.get(shutdown_restart_api, headers=headers).json()

                deviceRequestId = json_response["DeviceRequestid"]
                requestId = json_response["RequestID"]

                if requestId == 8:
                    url = f"https://deviceapi.cluemaster.io/api/Device/{unique_code}/{deviceRequestId}"
                    requests.post(url, headers=headers)
                    self.restart.emit()

                elif requestId == 9:
                    url = f"https://deviceapi.cluemaster.io/api/Device/{unique_code}/{deviceRequestId}"
                    requests.post(url, headers=headers)
                    self.shutdown.emit()

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls, then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the code inside the try is facing json decode error then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the code inside the try is facing simplejson decode error then pass
                pass

            except FileNotFoundError:
                # if the code faces the FilNotFoundError then pass
                pass

            finally:
                # and finally
                time.sleep(15)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsShutdownRestartRequestThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.restart.emit()


class UpdateRoomInfo(QThread):

    # signals
    update_detected = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        device_unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {device_unique_code}:{api_key}"

        get_room_info_api = f"https://deviceapi.cluemaster.io/api/Device/GetRoomInfo/{device_unique_code}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsUpdateRoomInfoThreadRunning"] is True:
                    pass

                else:
                    return

                print(">>> Console output - Update Room Info Response ")
                response_of_room_info_api = requests.get(get_room_info_api, headers=headers).json()

                dictionary = {"Room Minimum Players": response_of_room_info_api["RoomMinPlayers"],
                              "Room Maximum Players": response_of_room_info_api["RoomMaxPlayers"],
                              "Clues Allowed": response_of_room_info_api["CluesAllowed"],
                              "Clue Size On Screen": response_of_room_info_api["ClueSizeOnScreen"],
                              "Maximum Number Of Clues": response_of_room_info_api["MaxNoOfClues"],
                              "Clue Position Vertical": response_of_room_info_api["CluePositionVertical"],
                              "IsTimeLimit": response_of_room_info_api["IsTimeLimit"],
                              "Time Limit": response_of_room_info_api["TimeLimit"],
                              "Time Override": response_of_room_info_api["TimeOverride"],
                              "IsPhoto": response_of_room_info_api["IsPhoto"],
                              "IsFailVideo": response_of_room_info_api["IsFailVideo"],
                              "IsSuccessVideo": response_of_room_info_api["IsSuccessVideo"]}

                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/device configurations.json"), "w") as device_config_json_file:
                    json.dump(dictionary, device_config_json_file)

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the codes inside the try block faces json decode error then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the codes inside the try block faces simplejson decode error then pass
                pass

            except PermissionError:
                # application update detected
                self.update_detected.emit()

            else:
                # if no error then
                pass

            finally:
                # and finally
                time.sleep(10)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsUpdateRoomInfoThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.update_detected.emit()


class GetGameClue(QThread):

    # signals
    statusChanged = pyqtSignal()
    update_detected = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameDetails.json")) as game_details_json_file:
            initial_dictionary = json.load(game_details_json_file)

        game_details_response = initial_dictionary
        initial_gameId = game_details_response["gameId"]

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        device_unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {device_unique_code}:{api_key}"

        game_clue_url = f"https://deviceapi.cluemaster.io/api/Device/GetGameClue/{initial_gameId}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsGameClueThreadRunning"] is True:
                    pass

                else:
                    return

                print(">>> Console output - Clue response")
                json_response = requests.get(game_clue_url, headers=headers).json()
                gameClueId = json_response["gameClueId"]
                gameId = json_response["gameId"]

                requests.post(f"https://deviceapi.cluemaster.io/api/Device/PostGameClue/{gameId}/{gameClueId}", headers=headers)

                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/GameClue.json"), "w") as game_clue_json_file:
                    json.dump(json_response, game_clue_json_file)

                self.statusChanged.emit()

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls, then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the code inside the try is facing json decode error then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the code inside the try is facing simplejson decode error then pass
                pass

            except KeyError:
                # if the code inside the try block faces KeyError, then pass
                pass

            except PermissionError:
                # application update detected
                self.update_detected.emit()

            else:
                # if no error then
                pass

            finally:
                # and finally
                time.sleep(3)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsGameClueThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.update_detected.emit()


class GetTimerRequest(QThread):

    # signals
    updateTimer = pyqtSignal()
    update_detected = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        device_unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {device_unique_code}:{api_key}"

        get_timer_request_api = f"https://deviceapi.cluemaster.io/api/Device/GetTimerRequest/{device_unique_code}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsTimerRequestThreadRunning"] is True:
                    pass

                else:
                    return

                print(">>> Console output - Timer response")
                response = requests.get(get_timer_request_api, headers=headers).json()
                print(">>> Console output - Timer response ", response)

                request_id = response["DeviceRequestid"]
                device_key = response["DeviceKey"]
                requests.post(f"https://deviceapi.cluemaster.io/api/Device/{device_key}/{request_id}", headers=headers)

                self.updateTimer.emit()

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls, then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the code inside the try is facing json decode error then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the code inside the try is facing simplejson decode error then pass
                pass

            else:
                # if no error then
                pass

            finally:
                # and finally
                time.sleep(6)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsTimerRequestThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.update_detected.emit()


class DownloadConfigs(QThread):

    # signals
    downloadFiles = pyqtSignal()
    update_detected = pyqtSignal()

    def run(self):
        """ this is an autorun method which is triggered as soon as the thread is started, this method holds all the
            codes for every work, the thread does"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/unique_code.json")) as unique_code_json_file:
            initial_dictionary = json.load(unique_code_json_file)

        unique_code_response = initial_dictionary
        unique_code = unique_code_response["Device Unique Code"]
        api_key = unique_code_response["apiKey"]

        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Basic {unique_code}:{api_key}"

        download_files_request_api = f"https://deviceapi.cluemaster.io/api/Device/DownloadFilesRequest/{unique_code}"

        while True:
            try:
                with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as thread_file:
                    thread_file_response = json.load(thread_file)

                if thread_file_response["IsDownloadConfigsThreadRunning"] is True:
                    pass
                else:
                    return

                print(">>> Console Output - Download config response")
                response = requests.get(download_files_request_api, headers=headers).json()
                request_id = response["DeviceRequestid"]
                device_key = response["DeviceKey"]
                requests.post(f"https://deviceapi.cluemaster.io/api/Device/{device_key}/{request_id}", headers=headers)

                self.downloadFiles.emit()
                return

            except requests.exceptions.ConnectionError:
                # if the code inside the try block faces connection error while making api calls, then pass
                pass

            except json.decoder.JSONDecodeError:
                # if the code inside the try is facing json decode error then pass
                pass

            except simplejson.errors.JSONDecodeError:
                # if the code inside the try is facing simplejson decode error then pass
                pass

            except FileNotFoundError:
                # if the code faces the FilNotFoundError then pass
                pass

            finally:
                # and finally
                time.sleep(15)

    def stop(self):
        """this method when called updates the thread running status to False and in the next loop when the condition
           checks the status, the condition turns False and breaks the thread"""

        with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json")) as initial_thread_file:
            thread_file_response = json.load(initial_thread_file)

        thread_file_response["IsDownloadConfigsThreadRunning"] = False

        try:
            with open(os.path.join(MASTER_DIRECTORY, "assets/application data/ThreadInfo.json"), "w") as thread_file:
                json.dump(thread_file_response, thread_file)

        except PermissionError:
            self.update_detected.emit()

