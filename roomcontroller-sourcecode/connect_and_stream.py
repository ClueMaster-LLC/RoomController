import json
import threading
import socket
import time
from datetime import datetime, timedelta
import os
import platform
import requests
from apis import *
from requests.structures import CaseInsensitiveDict
import ncd_industrial_devices
import room_controller
import ast
import re

# This import will be for signalR code##
import logging
from signalrcore.hub_connection_builder import HubConnectionBuilder
from signalrcore.protocol.messagepack_protocol import MessagePackHubProtocol

##

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# GLOBAL VARIABLES

log_level = 0  # 0 for disabled | 1 for ALL details | 2 for device input/relay status | 3 for network connections


def function_relay(relay_val):
    relay_num = int(re.findall('[0-9]+', str(relay_val[0]))[0])
    return relay_num


class ConnectAndStream(threading.Thread):
    def __init__(self, device_mac):
        super(ConnectAndStream, self).__init__()
        # the ConnectAndStream thread is started after the ip address is saved in a file

        # local attributes inside ConnectAndStream
        self.game_status_old = None
        self.command_relay_list = []
        self.data_response_old = None
        self.signalr_bearer_token = None
        self.signalr_access_token = None
        self.active_input_values_old = None
        self.api_headers = None
        self.device_request_api_url = None
        self.api_bearer_key = None
        self.device_unique_id = None
        self.handler = None
        self.server_url = None
        self.hub_connection = None
        self.data_response = None
        self.active = None
        self.device_mac = device_mac
        [self.ip_address, self.server_port, self.device_model, self.device_type, self.read_speed, self.input_total,
         self.relay_total, self.room_id] = self.read_device_info(self.device_mac)
        room_controller.GLOBAL_ROOM_ID = self.room_id  # TODO remove this and add room_id to the RC config file from api.
        self.bank_total = ((self.input_total // 8) - 1)
        self.post_input_relay_request_update_api = POST_INPUT_RELAY_REQUEST_UPDATE
        self.roomcontroller_configs_file = os.path.join(APPLICATION_DATA_DIRECTORY, "roomcontroller_configs.json")
        self.unique_ids_file = os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")
        self.signalr_status = None
        self.client_socket = None
        self.ncd = None
        self.automation_rules = None
        self.automation_rules_file = os.path.join(APPLICATION_DATA_DIRECTORY, "automation_rules.json")
        self.command_resync = False
        self.startup_init = True
        self.command_relay_send = False
        self.command_reset_room = False

        # Diagnostic Only, global mac addresses to verify all threads can see them
        print(f">>> connect_and_stream - {self.device_mac} - GLOBAL MAC FOUND: {room_controller.global_active_mac_ids}")

        # instance methods
        self.configuration()

        # start signalR connections
        try:
            self.signalr_hub()
        except Exception as error:
            print(
                f">>> connect_and_stream - {self.device_mac} - SignalR Did not connect for Device. Server Error: {error}")

        print(f">>> connect_and_stream - {self.device_mac} - ***STARTUP COMPLETED***")

    def configuration(self):
        # Load the device ID's from the JSON file
        with open(self.unique_ids_file) as unique_ids_file:
            json_response_of_unique_ids_file = json.load(unique_ids_file)

        # Load the automation rules from the JSON file
        self.automation_rules_update()

        self.device_unique_id = json_response_of_unique_ids_file["device_id"]
        self.api_bearer_key = json_response_of_unique_ids_file["api_token"]
        self.device_request_api_url = ROOM_CONTROLLER_REQUEST_API.format(device_id=self.device_unique_id)

        self.api_headers = CaseInsensitiveDict()
        # self.api_headers["Authorization"] = f"Basic {self.device_unique_id}:{self.api_bearer_key}"
        self.signalr_bearer_token = f"?access_token={self.device_unique_id}_{self.api_bearer_key}"
        # self.signalr_access_token = f"?access_token=1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt"

    def signalr_hub(self):
        self.server_url = API_SIGNALR + self.signalr_bearer_token
        print(f">>> connect_and_stream - {self.device_mac} - SignalR connected to {API_SIGNALR}")
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.CRITICAL)
        self.hub_connection = HubConnectionBuilder() \
            .with_url(self.server_url, options={
            "verify_ssl": True,
            "skip_negotiation": False
        }) \
            .configure_logging(logging.CRITICAL, socket_trace=False, handler=self.handler) \
            .with_automatic_reconnect({
            "type": "raw",
            "keep_alive_interval": 5,
            "reconnect_interval": 10,
            "max_attempts": 3
        }).build()
        # TODO try to get retries working and connect to signalR when online
        # "accessTokenFactory": 'value'
        # "http_client_options": {"headers": self.api_headers, "timeout": 5.0},
        # "ws_client_options": {"headers": self.api_headers, "timeout": 5.0}
        # "type": "raw",
        # "type": "interval",
        # "keep_alive_interval": 5,
        # "reconnect_interval": 5,
        # "max_attempts": 99999999,
        # "intervals": [1, 3, 5, 6, 7, 87, 3]
        # .with_hub_protocol(MessagePackHubProtocol()) \

        self.hub_connection.on_close(lambda: (print(f">>> connect_and_stream - {self.device_mac} - "
                                                    f"SignalR Connection Closed")
                                              , self.signalr_connected(False)
                                              ))
        self.hub_connection.on_error(lambda data: (print(f">>> connect_and_stream - {self.device_mac} - "
                                                         f"A Server exception error was thrown: {data.error}")
                                                   ))
        self.hub_connection.on_open(lambda: (self.hub_connection.send('AddToGroup', [str(self.room_id)]),
                                             self.hub_connection.send('AddToGroup', [str(self.device_mac)]),
                                             print(f">>> connect_and_stream - {self.device_mac} - signalR handshake "
                                                   f"received. Ready to send/receive messages."),
                                             self.signalr_connected(True)
                                             ))
        self.hub_connection.on_reconnect(lambda: (print(f">>> connect_and_stream - {self.device_mac} - Trying to re-connect to"
                                                        f" {API_SIGNALR}")
                                                  ))

        self.hub_connection.start()

        while self.signalr_status is not True:
            for i in range(5, -1, -1):
                if self.signalr_status is True:
                    break
                if i == 0:
                    print(f'>>> connect_and_stream - {self.device_mac} - Timeout exceeded. SignalR not connected.')
                    break
                print(f'>>> connect_and_stream - {self.device_mac} - waiting for signalR handshake ... {i}')
                # print(self.server_url)
                time.sleep(1)
            break
        else:
            print(">>> connect_and_stream - signalr connected")

    def signalr_connected(self, status):
        if status is True:
            self.signalr_status = True
        elif not status:
            self.signalr_status = False

    def sync_data(self):
        # command received by hub to refresh values from all device threads to update location workspace
        self.command_resync = True
        self.hub_connection.send('sendtoroom', [str(self.room_id), str(self.device_mac), str(self.data_response)])
        self.command_resync = False

    # @property
    def run(self):
        connected = False
        while not connected:
            try:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                # print(">>> connect_and_stream - Room Controller IP Address: " + str(self.extract_ip()))
                print(f'>>> connect_and_stream - {self.device_mac} - Connecting to last known device IP: ',
                      self.ip_address, '  MAC: ', self.device_mac, '  Device Model: ', self.device_model,
                      '  Device Type: ', self.device_type)
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(1.0)
                self.client_socket.connect((self.ip_address, self.server_port))
                print(f'>>> connect_and_stream - {self.device_mac} - Connected IP: {self.ip_address}')
                connected = True

            except socket.error as error:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    self.client_socket.close()
                    print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                    return
                print(f'>>> connect_and_stream - {self.device_mac} Connection Error: {error}')
                print(f'>>> connect_and_stream - {self.device_mac} - The last known IP {self.ip_address} on PORT: '
                      f'{self.server_port} is no longer valid. Searching network for device... ')

                self.ip_address, self.server_port = self.device_discovery(self.device_mac)  # find new device IP Address
                print('>>> connect_and_stream - Connecting to ' + str(self.ip_address))
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(1.0)
                try:
                    self.client_socket.connect((self.ip_address, self.server_port))
                    connected = True
                except Exception as error:
                    print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(error))

            self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)
            # self.hub_connection.on('device_reboot', str(self.device_mac),
            #                        (lambda relay_num: (self.ncd.device_reboot())))

            # device_type 1 = Dry Contacts
            if self.device_type == 1:
                self.hub_connection.on('syncdata'
                                       , (lambda data:
                                          (self.sync_data()
                                           , print(f">>> connect_and_stream - {self.device_mac} - "
                                                   f"Re-Sync Data command received")
                                           )))

            # device_type 2 = Relays
            if self.device_type == 2:
                self.hub_connection.on('syncdata'
                                       , (lambda data:
                                          (relay_old_values_clear()
                                           , data_response_clear()
                                           , command_resync_true()
                                           , print(f">>> connect_and_stream - {self.device_mac} - "
                                                   f"Re-Sync Data command received")
                                           )))

                self.hub_connection.on('relay_on'
                                       , (lambda relay_num:
                                          (self.ncd.turn_on_relay_by_index(function_relay(relay_num))
                                           # , relay_trigger_update()
                                           , relay_send_true()
                                           , relay_old_values_clear()
                                           , data_response_clear()
                                           , print(f'>>> connect_and_stream - {self.device_mac} - '
                                                   f'RELAY ON # {function_relay(relay_num)}')
                                           )))
                self.hub_connection.on('relay_off'
                                       , (lambda relay_num:
                                          (self.ncd.turn_off_relay_by_index(function_relay(relay_num))
                                           # , relay_trigger_update()
                                           , relay_send_true()
                                           , relay_old_values_clear()
                                           , data_response_clear()
                                           , print(f'>>> connect_and_stream - {self.device_mac} - '
                                                   f'RELAY OFF # {function_relay(relay_num)}')
                                           )))

                self.hub_connection.on('reset_room'
                                       , (lambda data: (relay_old_values_clear()
                                                        , data_response_clear()
                                                        , command_reset_room()
                                                        , print(f">>> connect_and_stream - {self.device_mac}"
                                                                f" Reset Room command received")
                                                        )))

                self.hub_connection.on('reset_puzzles'
                                       , (lambda data: (self.ncd.set_relay_bank_status(0, 0)
                                                        , relay_old_values_clear()
                                                        , data_response_clear()
                                                        , command_reset_puzzles()
                                                        , print(f">>> connect_and_stream - {self.device_mac}"
                                                                f" Reset Puzzles command received")
                                                        )))

                self.hub_connection.on('relay_pulse'
                                       , (lambda relay_num, pulse_time=.1:
                                          (self.ncd.turn_on_relay_by_index(function_relay(relay_num))
                                           , time.sleep(pulse_time)
                                           , self.ncd.turn_off_relay_by_index(function_relay(relay_num))
                                           , print(f'>>> connect_and_stream - {self.device_mac} - '
                                                   f'RELAY PULSE ON/OFF # {function_relay(relay_num)}'
                                                   f' for ({pulse_time} second)')
                                           )))

                # self.hub_connection.on('relay_off_pulse'
                #                        , (lambda relay_num, pulse_time=.1:
                #                           (self.ncd.turn_off_relay_by_index(function_relay(relay_num))
                #                            , time.sleep(pulse_time)
                #                            , self.ncd.turn_on_relay_by_index(function_relay(relay_num))
                #                            , print(f'>>> connect_and_stream - {self.device_mac} - '
                #                                    f'RELAY PULSE OFF/ON # {function_relay(relay_num)}'
                #                                    f' for ({pulse_time} second)')
                #                            )))

                def relay_multi_command(relay_array):
                    for relay in relay_array:
                        print(f'do it now {relay}')

                def relay_old_values_clear():
                    self.active_input_values_old = None

                def data_response_clear():
                    # self.data_response = []
                    self.data_response_old = None

                def command_resync_true():
                    self.command_resync = True

                def command_reset_room():
                    self.command_reset_room = True

                    # clearing of active automations in memory pending
                    # Added 10-06-2024 - by: Robert
                    self.command_relay_list.clear()

                def command_reset_puzzles():
                    self.command_reset_room = True

                    # clearing of active automations in memory pending
                    # Added 10-06-2024 - by: Robert
                    self.command_relay_list.clear()

                def relay_send_true():
                    self.command_relay_send = True

        try:
            self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)
            try:
                # to clear the buffer on NIC when first connect sends MAC.
                data_response_init = self.client_socket.recvfrom(32)
                data_response_mac = str(list(data_response_init)[0]).replace(":", '').replace("b'", '').replace("'", '')

                if data_response_mac == self.device_mac:
                    # print(f'>>> connect_and_stream - {self.device_mac} - VALUES MATCH')
                    pass
                else:
                    print(
                        f'>>> connect_and_stream - {self.device_mac} - EXPECTED MAC VALUES DONT MATCH {data_response_mac}')
                    self.client_socket.close()
                    print(f'>>> connect_and_stream - {self.device_mac} - Disconnecting from {self.ip_address}')
                    self.update_webapp_with_new_details(ip_address='0.0.0.0', macaddress=self.device_mac,
                                                        serverport='2101')
                    print(f'>>> connect_and_stream - {self.device_mac} - The last known IP {self.ip_address}'
                          f' is no longer valid. Searching network for device... ')
                    self.ip_address, self.server_port = self.device_discovery(
                        self.device_mac)  # find new device IP Address
                    print(f'>>> connect_and_stream - {self.device_mac} - Connecting to {self.ip_address}')

                    if self.device_mac not in room_controller.global_active_mac_ids:
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        # self.hub_connection.stop()
                        return
                    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client_socket.settimeout(1.0)
                    self.client_socket.connect((self.ip_address, self.server_port))

                    # Verify communication and clear nic buffer to get rid of FALSE response
                    self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)

                    try:
                        # to clear the buffer on NIC when first connect sends MAC.
                        self.client_socket.recvfrom(32)
                    except Exception as e:
                        print('>>> connect_and_stream - ', self.device_mac, ' Socket Buffer Error: ', str(e))

                    self.ncd.test_comms()
                    print(f'>>> connect_and_stream - {self.device_mac} - Connected to IP: {self.ip_address}')

            except Exception as e:
                print('>>> connect_and_stream - init ERROR: ' + str(e))
                data_response_init = self.device_mac

            self.data_response_old = None
            # self.active_input_values_old = None

            print(f">>> connect_and_stream - {self.device_mac} - DEVICE CONNECTED AND READY")

            while self.device_mac in room_controller.global_active_mac_ids:
                # print("start processing loop")
                try:

                    if self.device_type == 2:
                        # Change type to 2 for relay boards.  Using 1 for testing only on DC thread
                        # print("IM WAITING FORE RELAY COMMANDS")
                        # loop here and do nothing but check for connection to the relay board.
                        # signalR will fire in the background when needed.
                        # print(f">>> connect_and_stream - {self.device_mac} - DEVICE IS TYPE {self.device_type}")
                        # self.ncd.test_comms()

                        # print(f">>> connect_and_stream - {self.device_mac} - NCD DEVICE COMMS TEST SUCCESSFUL")
                        # print(f">>> connect_and_stream - {self.device_mac} - {room_controller.ACTIVE_INPUT_VALUES}")

                        # DOWNLOAD NEW AUTOMATION RULES AND PUT IN ACTIVE MEMORY WITHOUT RESTARTING
                        if room_controller.GLOBAL_AUTOMATION_RULE_PENDING:
                            print(f">>> connect_and_stream - {self.device_mac} - New Automation Rules Ready for DL")
                            self.automation_rules_update()

                        # Define a function to check if a given condition is true
                        def check_condition(condition):
                            if 'type' in condition and condition['type'] == 'group':
                                # Group condition
                                conditions = condition['conditions']
                                operator = condition['operator']

                                # Check if all sub-conditions satisfy the operator
                                sub_results = [check_condition(sub_condition) for sub_condition in conditions]
                                if operator == 'and':
                                    result = all(sub_results)
                                elif operator == 'or':
                                    result = any(sub_results)
                                else:
                                    print(f"Invalid operator {operator}")
                                    result = False
                            else:
                                # Sensor condition
                                event_type = condition['event_type']

                                if event_type == 'device':
                                    device_name = condition['device']
                                    sensor_inputs = condition['inputs']
                                    operator = condition['operator']
                                    value = condition['value']
                                    # Find the sensor in the global variable
                                    for sensor in room_controller.ACTIVE_INPUT_VALUES:
                                        if sensor[0] == device_name:
                                            sensor_values = sensor[1]
                                            break
                                    else:
                                        print(f">>> connect_and_stream - {self.device_mac} - Sensor {device_name}"
                                              f" not found in global variable")
                                        return False

                                    # Check if the inputs satisfy the condition
                                    input_statuses = []
                                    for bank_value in sensor_values:
                                        input_statuses += [(bank_value >> i) & 1 for i in range(8)]

                                    input_values = [input_statuses[i - 1] for i in sensor_inputs]

                                    if operator == 'and':
                                        result = all(input_values) == value
                                    elif operator == 'or':
                                        result = any(input_values) == value
                                    else:
                                        print(f"Invalid operator {operator}")
                                        result = False

                                elif event_type == 'system':
                                    operator = condition['operator']
                                    game_status = condition['game_status']
                                    value = condition['value']

                                    # print(
                                    #     f"-------------CURRENT GLOBAL GAME STATUS: {room_controller.GLOBAL_GAME_STATUS}")
                                    # print(f"-------------LOOKING FOR GAME VALUES: {game_status}")

                                    # Check if the inputs satisfy the condition
                                    game_value = [1 if item in [room_controller.GLOBAL_GAME_STATUS] else 0
                                                  for item in game_status]

                                    if operator == 'and':
                                        result = all(game_value) == value
                                        # print(f">>> connect_and_stream - {self.device_mac} - RESULT"
                                        #       f" {result} WITH {game_value} == {value}")
                                    elif operator == 'or':
                                        result = any(game_value) == value
                                        # print(f">>> connect_and_stream - {self.device_mac} - RESULT"
                                        #       f" {result} WITH {game_value} == {value}")
                                    else:
                                        print(f"Invalid operator {operator}")
                                        result = False
                                else:
                                    result = False
                                # print(f"-------------FOUND GAME FINAL RETURNED VALUE: {result}")
                            return result

                        # Define a function to execute a given action
                        def execute_action(action):
                            current_datetime = datetime.now()
                            # print("Current date and time:", current_datetime)

                            device_name = action['device']
                            relay_num = int(action['relay'])
                            relay_delay = int(action['delay'])
                            relay_action = action['action']

                            # Convert milliseconds to a timedelta object
                            millisecond_timedelta = timedelta(milliseconds=relay_delay)
                            # print("Current TIME DELTA:", millisecond_timedelta)

                            # Add 5 seconds to the current time
                            scheduled_datetime = current_datetime + millisecond_timedelta
                            # print("Current FUTURE DATETIME:", scheduled_datetime)

                            # Append additional relay commands to list to queue up.
                            if device_name == self.device_mac:
                                self.command_relay_list.append([device_name, scheduled_datetime, relay_num
                                                                   , relay_action, relay_delay])

                        # Check all automation rules on every value change of inputs/relays
                        def run_automation_rules():
                            for rule in self.automation_rules['rules']:
                                rule_name = rule['name']
                                conditions = rule['conditions']
                                actions = rule['actions']

                                # Check if all conditions are true
                                all_conditions_true = all(check_condition(condition) for condition in conditions)

                                # TODO monitor to see if we need to allow for resync command too?
                                if not self.command_resync and not self.startup_init:
                                    # Execute actions if all conditions are true
                                    if all_conditions_true:
                                        # Check if this rule has already fired
                                        if 'fired' not in rule or not rule['fired']:
                                            # Execute all actions
                                            for action in actions:
                                                execute_action(action)
                                                self.data_response_old = None

                                            # Set fired flag to True
                                            rule['fired'] = True
                                            print(f">>> connect_and_stream - {self.device_mac} - "
                                                  f"Running Rule:  {rule_name}")
                                    else:
                                        # Set fired flag to False
                                        rule['fired'] = False

                        # if GLOBAL GAME STATUS changes then run automation rules
                        if self.game_status_old != room_controller.GLOBAL_GAME_STATUS:
                            # print(f">>> connect_and_stream - {self.device_mac} - GameStatus Changed:"
                            #       f" NEW: {room_controller.GLOBAL_GAME_STATUS} and OLD: {self.game_status_old}")
                            run_automation_rules()
                            self.game_status_old = room_controller.GLOBAL_GAME_STATUS

                        # if room_controller.ACTIVE_INPUT_VALUES change
                        if self.active_input_values_old != str(room_controller.ACTIVE_INPUT_VALUES):

                            # print(f">>> connect_and_stream - {self.device_mac} -
                            # {room_controller.ACTIVE_INPUT_VALUES} CURRENT VALUES")
                            # print(f">>> connect_and_stream - {self.device_mac} -
                            # {self.active_input_values_old} OLD HAVE CHANGED")

                            # Set the var to what is in the GLOBAL var for active input values to stop loop
                            self.active_input_values_old = str(room_controller.ACTIVE_INPUT_VALUES)

                            # Check status of relays after automation and report to SignalR
                            self.data_response = self.ncd.get_relay_all_bank_status()

                            if not self.data_response:
                                print(f"{self.data_response} SENDING DATA TO RELAY TOO FAST. CPU TIMEOUT")
                                print(f">>> connect_and_stream - {self.device_mac} - "
                                      f"DATA RESPONSE IS: {self.data_response}")
                                self.client_socket.close()
                                time.sleep(1)
                                # self.ncd.renew_replace_interface(self.client_socket)
                                pass

                            if self.data_response_old != self.data_response:
                                self.data_response_old = self.data_response

                                # load input device values into global variable to use for automation
                                device_value = (self.device_mac, self.data_response)

                                if device_value[0] not in [device[0] for device in room_controller.ACTIVE_INPUT_VALUES]:
                                    room_controller.ACTIVE_INPUT_VALUES.append(device_value)
                                else:
                                    for device in room_controller.ACTIVE_INPUT_VALUES:  # looping through every record
                                        # checking if update mac address in present in each looped device
                                        if device_value[0] in device:  # if mac matches then check if the update
                                            # data is the same or not
                                            if device_value[1] == device[1]:  # if yes, then pass
                                                pass
                                            else:  # update with new values
                                                device[1].clear()
                                                device[1].extend(device_value[1])
                                                # print(room_controller.ACTIVE_INPUT_VALUES)
                                        else:
                                            pass

                                # upload relay changes to SignalR
                                if self.signalr_status:
                                    try:

                                        if not self.command_relay_send:
                                            print(f">>> connect_and_stream - {self.device_mac} - "
                                                  f"SEND RELAY VALUES TO CLUEMASTER - "
                                                  f"SignalR > [{self.room_id}, {self.device_mac}, {self.data_response}]")

                                            # send data to signalR hub
                                            self.hub_connection.send('sendtoroom', [str(self.room_id),
                                                                                    str(self.device_mac),
                                                                                    str(self.data_response)])

                                        try:
                                            # print(f">>> connect_and_stream - {self.device_mac} - {self.command_resync},"
                                            #       f" {self.startup_init}, {self.command_relay_send}")
                                            if not self.command_resync and not self.startup_init and not self.command_reset_room:
                                                print(f">>> connect_and_stream - {self.device_mac} - "
                                                      f"SEND RELAY TRIGGER VALUES TO CLUEMASTER - "
                                                      f"SignalR > [{self.room_id}, "
                                                      f"{self.device_mac}, "
                                                      f"{self.data_response}]")

                                                # send trigger data to signalR hub
                                                self.hub_connection.send('SendClueTrigger', [str(self.room_id),
                                                                                             str(self.device_mac),
                                                                                             str(self.data_response)])

                                        except Exception as error:
                                            print(f'>>> connect_and_stream - {self.device_mac} SignalR Error: {error}')

                                        # Setting resync command to false so that when refreshing the website,
                                        # it won't cause a trigger to fire.
                                        self.command_resync = False
                                        self.command_relay_send = False
                                        self.command_reset_room = False

                                    except Exception as error:
                                        print(f'>>> connect_and_stream - {self.device_mac} Connection Error: {error}')
                                else:
                                    print('>>> connect_and_stream - SIGNALR IS NOT CONNECTED > '
                                          , [str(self.room_id), str(self.device_mac), str(self.data_response)])
                                    try:
                                        self.hub_connection.start()
                                    except Exception as error:
                                        print(
                                            f'>>> connect_and_stream - {self.device_mac} SignalR Connection Error: {error}')

                            # run automation rules if they need to fire
                            run_automation_rules()

                        # start checking list to see if we have commands to fire for relays
                        if self.command_relay_list != []:
                            # local variables
                            current_datetime = datetime.now()

                            # run the relay commands in a loop from list until empty
                            def execute_relay_action(relay_number, relay_actions, delay):
                                # Perform the relay action
                                if relay_actions == 'on':
                                    self.ncd.turn_on_relay_by_index(relay_number)
                                    print(f">>> connect_and_stream - {self.device_mac} "
                                          f"- AUTOMATION ACTION ({relay_actions})"
                                          f" ON RELAY # ({relay_number})"
                                          f" AFTER ({delay*0.001}) SECONDS.")
                                elif relay_actions == 'off':
                                    if relay_number == 0:
                                        self.ncd.set_relay_bank_status(0, 0)
                                    else:
                                        self.ncd.turn_off_relay_by_index(relay_number)
                                        print(f">>> connect_and_stream - {self.device_mac} "
                                              f"- AUTOMATION ACTION ({relay_actions})"
                                              f" ON RELAY # ({relay_number})"
                                              f" AFTER ({delay*0.001}) SECONDS.")

                            for command in self.command_relay_list:
                                device_name, scheduled_datetime, relay_num, relay_action, relay_delay = command
                                
                                try:
                                    if current_datetime >= scheduled_datetime:
                                        execute_relay_action(relay_num, relay_action, relay_delay)

                                        # TODO: We might need to slow down the commands if they run too fast
                                        # time.sleep(0.01)

                                        # Remove the command from the list once it has been executed
                                        if self.command_relay_list == []:
                                            pass
                                        else:
                                            self.command_relay_list.remove(command)

                                except Exception as error:
                                    print(f">>> connect_and_stream - {self.device_mac} - Relay Timer Command:"
                                          f" {error}")

                            # Clear out old relay values incase they have changed and on next loop it will check
                            # and send new values to signalR for GM Workspace to update puzzles linked to relays.
                            relay_old_values_clear()

                        # Wait for some time before checking again
                        # TODO: See if we need to sleep to slow cpu usage and add NCD.COMMS check.
                        #  Maybe set to 0.05. This is the loop to check for automations. Too fast will eat 100% cpu
                        #  in the loop as it checks.
                        time.sleep(0.05)

                    elif self.device_type == 1:

                        self.data_response = (self.ncd.get_dc_bank_status(0, self.bank_total))
                        # data_response_new = self.data_response
                        if not self.data_response:
                            print(f'DATA RESPONSE IS: {self.data_response}')

                        if self.data_response_old != self.data_response:
                            self.data_response_old = self.data_response

                            # load input device values into global variable to use for automation
                            device_value = (self.device_mac, self.data_response)
                            devices_info = room_controller.ACTIVE_INPUT_VALUES
                            # update = device_value

                            if device_value[0] not in [device[0] for device in room_controller.ACTIVE_INPUT_VALUES]:
                                room_controller.ACTIVE_INPUT_VALUES.append(device_value)
                            else:
                                for device in room_controller.ACTIVE_INPUT_VALUES:  # looping through every record
                                    # checking if update mac address in present in each looped device
                                    if device_value[0] in device:  # if mac matches then check if the update
                                        # data is the same or not
                                        if device_value[1] == device[1]:  # if yes, then pass
                                            pass
                                        else:  # update with new values
                                            device[1].clear()
                                            device[1].extend(device_value[1])
                                    else:
                                        pass

                            # print(devices_info)
                            # set the global variable for ACTIVE_INPUT_VALUES to be used by other threads
                            # room_controller.ACTIVE_INPUT_VALUES = device_value
                            # print('>>> connect_and_stream - ', self.device_mac, ' - ACTIVE GLOBAL INPUTS: ',
                            #       room_controller.ACTIVE_INPUT_VALUES)
                            # print(f">>> connect_and_stream - {self.device_mac} - ACTIVE GLOBAL INPUTS: {room_controller.ACTIVE_INPUT_VALUES}")

                            if self.signalr_status:
                                try:
                                    print(f">>> connect_and_stream - {self.device_mac} - SEND VALUES TO CLUEMASTER"
                                          f" SignalR > [{self.room_id}, {self.device_mac}, {self.data_response}]")

                                    # send data to signalR hub
                                    self.hub_connection.send('sendtoroom', [str(self.room_id),
                                                                            str(self.device_mac),
                                                                            str(self.data_response)])

                                    try:
                                        # print(self.command_resync, self.startup_init)
                                        if not self.command_resync and not self.startup_init:
                                            print(f">>> connect_and_stream - {self.device_mac} - "
                                                  f"SEND TRIGGER VALUES TO CLUEMASTER"
                                                  f" SignalR > [{self.room_id}, {self.device_mac}, {self.data_response}]")

                                            # send trigger data to signalR hub
                                            self.hub_connection.send('SendClueTrigger', [str(self.room_id),
                                                                                         str(self.device_mac),
                                                                                         str(self.data_response)])

                                    except Exception as error:
                                        print(f'>>> connect_and_stream - {self.device_mac} SignalR Error: {error}')

                                except Exception as error:
                                    print(f'>>> connect_and_stream - {self.device_mac} SignalR Error: {error}')
                            else:
                                print('>>> connect_and_stream - SIGNALR IS NOT CONNECTED > '
                                      , [str(self.room_id), str(self.device_mac), str(self.data_response)])
                                try:
                                    self.hub_connection.start()
                                except Exception as error:
                                    print(
                                        f'>>> connect_and_stream - {self.device_mac} SignalR Connection Error: {error}')

                            # if log_level in (1, 2):
                            #     print('>>> connect_and_stream - HEX BYTE VALUES RETURNED FROM DEVICE ',
                            #           str(bytes(self.data_response)))
                            #     print('>>> connect_and_stream - LIST VALUES RETURNED FROM DEVICE ',
                            #           str(self.data_response))
                            #
                            #     # make a new array by ignoring the first two bytes and the last byte
                            #     readings = bytes(self.data_response)
                            #     counter = 0
                            #     bytes_as_bits = ''.join(format(byte, '08b') for byte in readings)
                            #     print('>>> connect_and_stream - Binary Response Values : ', bytes_as_bits)
                            #
                            #     # This code block is only for displaying the of/off of the inputs to the log for
                            #     # diagnostics
                            #     for bank in readings:
                            #         # increment through each input
                            #         for i in range(0, self.input_total):
                            #             # << indicates a bit shift. Basically check corresponding bit in the reading
                            #             state = (bank & (1 << i))
                            #             if state != 0:
                            #                 # print('Input '+ str(bank) +' is high')
                            #                 print('>>> connect_and_stream - BANK Unknown: Input ' + str(
                            #                     i + 1) + ' is high')
                            #             else:
                            #                 print('>>> connect_and_stream - BANK Unknown: Input ' + str(
                            #                     i + 1) + ' is low')
                            #             counter += 1

                        # wait for a few defined seconds
                        time.sleep(self.read_speed * 0.001)

                    else:
                        # terminating thread
                        try:
                            self.client_socket.close()
                            self.hub_connection.stop()
                        except Exception as error:
                            print(f'>>> connect_and_stream - {self.device_mac} Error: {error}')
                        if self.device_type not in (1, 2):
                            print(f'>>> connect_and_stream - ', self.device_mac,
                                  f' Error: Device Type {self.device_type} Not Compatible')
                        print(f'>>> connect_and_stream - {self.device_mac} - 1+Closing Thread for ', self.device_mac)
                        return

                except socket.error:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        try:
                            self.client_socket.close()
                            self.hub_connection.stop()
                        except Exception as error:
                            print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(error))
                        print(">>> connect_and_stream - 2+Closing Thread for " + self.device_mac)
                        return
                    # set connection status and recreate socket
                    connected = False
                    while not connected:
                        try:
                            if self.device_mac not in room_controller.global_active_mac_ids:
                                print(">>> connect_and_stream - 3+Closing Thread for " + self.device_mac)
                                return
                            self.client_socket.close()
                            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.client_socket.settimeout(1.0)
                            self.client_socket.connect((self.ip_address, self.server_port))

                            # Verify communication and clear nic buffer to get rid of FALSE response
                            self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)

                            try:
                                # to clear the buffer on NIC when first connect sends MAC.
                                self.client_socket.recvfrom(32)
                            except Exception as e:
                                print('>>> connect_and_stream - ', self.device_mac, ' Socket Buffer Error: ', str(e))

                            self.ncd.test_comms()
                            print(f'>>> connect_and_stream - {self.device_mac} - Connected to IP: {self.ip_address}')
                            connected = True

                        except socket.error as e:
                            if self.device_mac not in room_controller.global_active_mac_ids:
                                self.client_socket.close()
                                print(">>> connect_and_stream - 4+Closing Thread for " + self.device_mac)
                                return
                            print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))
                            self.connection_lost()

                except Exception as e:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        try:
                            self.client_socket.close()
                            self.hub_connection.stop()
                        except Exception as error:
                            print(f'>>> connect_and_stream - {self.device_mac} - {error}')
                        print(">>> connect_and_stream - 5+Closing Thread for " + self.device_mac)
                        return
                    print(f'>>> connect_and_stream - {self.device_mac} - Error: {e}')

                # Run is finished starting and begins loop
                self.startup_init = False

            # MAC Address no longer in active memory.
            try:
                self.client_socket.close()
                if self.signalr_status:
                    self.hub_connection.stop()
                    time.sleep(1)

            except Exception as error:
                print(f'>>> connect_and_stream - {self.device_mac} - {error}')

            print(">>> connect_and_stream - 6+Closing Thread for " + self.device_mac)
            return

        except socket.error:
            if self.device_mac not in room_controller.global_active_mac_ids:
                try:
                    self.client_socket.close()
                    if self.signalr_status:
                        self.hub_connection.stop()
                        time.sleep(1)
                except Exception as error:
                    print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(error))
                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                return
            # set connection status and recreate socket
            connected = False
            while not connected:
                try:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return
                    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client_socket.settimeout(1.0)
                    self.client_socket.connect((self.ip_address, self.server_port))

                    # Verify communication and clear nic buffer to get rid of FALSE response
                    self.ncd = ncd_industrial_devices.NCD_Controller(self.client_socket)

                    try:
                        # to clear the buffer on NIC when first connect sends MAC.
                        self.client_socket.recvfrom(32)
                    except Exception as e:
                        print('>>> connect_and_stream - ', self.device_mac, ' Socket Buffer Error: ', str(e))

                    self.ncd.test_comms()
                    print(f'>>> connect_and_stream - {self.device_mac} - Connected to IP: {self.ip_address}')
                    connected = True

                except socket.error as e:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        self.client_socket.close()
                        print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                        return
                    print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))
                    self.connection_lost()

        except Exception as e:
            if self.device_mac not in room_controller.global_active_mac_ids:
                try:
                    self.client_socket.close()
                    if self.signalr_status:
                        self.hub_connection.stop()
                        time.sleep(1)
                except Exception as error:
                    print(error)
                print(">>> connect_and_stream - Closing Thread for " + self.device_mac)
                return

    def connection_lost(self):
        # set connection status and recreate socket
        connected = False
        connect_retry = 15
        # self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.client_socket.settimeout(1.0)
        # try:
        #     # to clear the buffer on NIC when first connect sends MAC.
        #     self.client_socket.recvfrom(32)
        # except Exception as e:
        #     print('>>> connect_and_stream - Connection Lost Error: ' + str(e))
        #     # data_response_init = self.device_mac
        # self.client_socket.close()
        # time.sleep(1)
        print('>>> connect_and_stream - connection lost... reconnecting')
        while not connected:
            # attempt to reconnect, otherwise loop for 15 seconds
            try:
                if self.device_mac not in room_controller.global_active_mac_ids:
                    self.client_socket.close()
                    print(">>> connect_and_stream - Closing Lost Connection Thread for " + self.device_mac)
                    return
                self.client_socket.close()
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(1.0)
                self.client_socket.connect((self.ip_address, self.server_port))
                # try:
                #     # to clear the buffer on NIC when first connect sends MAC.
                #     self.client_socket.recvfrom(32)
                # except Exception as e:
                #     print('>>> connect_and_stream - ', self.device_mac, ' Connection Error: ', str(e))

                connected = True
                print('>>> connect_and_stream - re-connection successful to ' + str(self.device_mac))
                self.client_socket.close()
                time.sleep(1)
            except socket.error:
                print(">>> connect_and_stream - " + str(self.device_mac) + ": searching..." + str(connect_retry))
                connect_retry -= 1
                if connect_retry == 0:
                    print('>>> connect_and_stream - Connection Lost. Starting Network Discovery Search')
                    self.device_discovery(self.device_mac)
                    time.sleep(1)
                    break

    def device_discovery(self, device_mac):
        try:
            local_ip = self.extract_ip()
            local_port = 13000
            buffer_size = 1024
            print(f'>>> connect_and_stream - {self.device_mac} - SCANNING NETWORK USING LOCAL IP: {local_ip} '
                  f'ON PORT: {local_port}')

            # msgFromServer = "Connected"
            # bytesToSend = str.encode(msgFromServer)

            # Create a datagram socket
            udp_server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            udp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to address and ip
            if platform.system() == "Windows":
                udp_server_socket.bind((local_ip, local_port))
            elif platform.system() == "Linux" or platform.system() == "Linux2":
                # Bind to address and ip
                udp_server_socket.bind(("<broadcast>", local_port))

            # Listen for incoming datagrams
            while True:
                try:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        udp_server_socket.close()
                        print(f">>> connect_and_stream - {self.device_mac} - Closing Discovery"
                              f" Thread for {self.device_mac}")
                        return

                    print(f">>> connect_and_stream - {self.device_mac} - {datetime.utcnow()}"
                          f" - UDP Network Search for: {device_mac}")
                    udp_server_socket.settimeout(15)
                    bytes_address_pair = udp_server_socket.recvfrom(buffer_size)

                    if log_level in (1, 3):
                        print(bytes_address_pair)
                        print(list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))
                    # data returned# ['192.168.1.19', '0008DC21DDFD', '2101', 'NCD.IO', '2.4 (IP, PORT)
                    # \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
                    # \\x00\\x00\\x00\\x00\\x00']

                    discover_ip = ((bytes_address_pair[1])[0])
                    discover_mac = (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[1]
                    discover_port = \
                        int((list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[2])
                    # We are using the model from the json file for now
                    # discovery_model = \
                    #     (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[3]
                    discovery_version = \
                        (list("{}".format(bytes_address_pair[0])[2:-1].replace("\\x00", "").split(",")))[4]
                    discover_model = self.device_model
                    discover_device_type = self.device_type

                    if discover_mac == self.device_mac:
                        try:
                            print(">>> connect_and_stream - Discovered Device IP:  ", discover_ip)
                            print(">>> connect_and_stream - Discovered Device MAC: ", discover_mac)
                            print(">>> connect_and_stream - Discovered Device Port: ", discover_port)
                            print(">>> connect_and_stream - Discovered Device Model: ", discover_model)
                            print(">>> connect_and_stream - Discovered Device Type: ", discover_device_type)
                            print(">>> connect_and_stream - Discovered Device Network Card Firmware Version: ",
                                  discovery_version)
                            print(">>> connect_and_stream - Saving updated device info to file.")

                            # Write new updated IP to local file
                            try:
                                self.save_device_info(discover_ip, discover_mac, discover_port)
                            except Exception as error:
                                print(f'>>> connect_and_stream - {self.device_mac} - Error: Unable to save updated '
                                      f'device info to file. - {error}')
                            try:
                                self.update_webapp_with_new_details(ip_address=discover_ip, macaddress=discover_mac,
                                                                    serverport=discover_port)
                            except Exception as error:
                                print(f'>>> connect_and_stream - {self.device_mac}: {error}')

                            udp_server_socket.close()
                            time.sleep(1)
                            break
                        except Exception as e:
                            print(f'>>> connect_and_stream - {self.device_mac}: {e}')
                    else:
                        if self.device_mac not in room_controller.global_active_mac_ids:
                            udp_server_socket.close()
                            print(f'>>> connect_and_stream - {self.device_mac} - Closing Discovery Thread')
                            return
                        print(">>> connect_and_stream - " + str(datetime.now()) + " - Device: " + str(
                            device_mac) + " not found on network. Continuing to search...")

                    # break
                except socket.error:  # change to exception:
                    if self.device_mac not in room_controller.global_active_mac_ids:
                        udp_server_socket.close()
                        print(f'>>> connect_and_stream - {self.device_mac} - Closing Discovery '
                              f'Thread for {self.device_mac}')
                        return
                    print(">>> connect_and_stream - UDP Search Timeout Reached - Device not found")
                    # set connection status and recreate socket
                    # self.device_discovery(device_mac)
                    # self.run()

            # print("done with discovery loop")

        except Exception as e:
            if self.device_mac not in room_controller.global_active_mac_ids:
                try:
                    udp_server_socket.close()
                    print(f'>>> connect_and_stream - {self.device_mac} - UDP Socket Closed on {self.ip_address}')
                except socket.error as e:
                    print(f'>>> connect_and_stream - {self.device_mac} - Error closing port: {e} on {self.ip_address}')

                print(f'>>> connect_and_stream - {self.device_mac} - CLOSING DISCOVERY THREAD')
                return
            print(f'>>> connect_and_stream - {self.device_mac} - {e}')
            print(f'>>> connect_and_stream - {self.device_mac} - Error trying to open UDP discovery port')
            # set connection status and recreate socket
            # self.connection_lost()

        return discover_ip, discover_port

    def automation_rules_update(self):
        try:
            with open(self.automation_rules_file, 'r') as f:
                self.automation_rules = json.load(f)
                print(f">>> connect_and_stream - {self.device_mac} - Automation Rules Loaded Successfully")
                room_controller.GLOBAL_AUTOMATION_RULE_PENDING = False

        except Exception as error:
            print(">>> connect_and_stream - ", self.device_mac,
                  f" Failed to Load Automation Rules File or File Does Not Exist. {error}")

    @staticmethod
    def extract_ip():
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            st.connect(('10.255.255.255', 1))
            ip_address = st.getsockname()[0]
        except socket.error:
            ip_address = '127.0.0.1'
            print(">>> connect_and_stream - Error trying to find Room Controller IP, Defaulting to 127.0.0.1")
        except Exception:
            ip_address = '127.0.0.1'
            print(">>> connect_and_stream - Error trying to find Room Controller IP, Defaulting to 127.0.0.1")
        finally:
            st.close()
        return ip_address

    @staticmethod
    def reboot_device():
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ncd = ncd_industrial_devices.NCD_Controller(client_socket)
            try:
                data_response_init = client_socket.recvfrom(32)
                print(str(data_response_init))
                # to clear the buffer on NIC when first connect sends MAC.
            except Exception as e:
                print('>>> connect_and_stream - ' + str(e))
                # data_response_init = self.device_mac
            ncd.device_reboot()
            client_socket.close()
            print(">>> connect_and_stream - Device Rebooted")

        except socket.error:
            print(">>> connect_and_stream - Error Sending Reboot Command")

    @staticmethod
    def save_device_info(ip, i_mac, port):
        device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
        with open(device_info_file) as connected_devices_file:
            connected_devices_file_response = json.load(connected_devices_file)
            for device in connected_devices_file_response["Devices"]:
                if device["MacAddress"] == i_mac:
                    print(f">>> connect_and_stream - Updating IP and PORT of {i_mac} in JSON file.")
                    device["IP"] = str(ip)
                    device["ServerPort"] = int(port)

        with open(device_info_file, "w") as connected_devices_file:
            json.dump(connected_devices_file_response, connected_devices_file)

    @staticmethod
    def read_device_info(i_mac):
        try:
            device_info_file = os.path.join(APPLICATION_DATA_DIRECTORY, "connected_devices.json")
            with open(device_info_file) as connected_devices_file:
                connected_devices_file_response = json.load(connected_devices_file)
                for values in connected_devices_file_response["Devices"]:
                    device_mac_address = values["MacAddress"]
                    if device_mac_address == i_mac:
                        print(">>> connect_and_stream - Device record exists for : ", i_mac)
                        return values["IP"], values["ServerPort"], values["DeviceModel"], values["DeviceType"], values[
                            "ReadSpeed"], values["InputTotal"], values["RelayTotal"], values["RoomID"]
                        # exit()

        except Exception as e:
            print('>>> connect_and_stream - ' + str(e))
            print(">>> connect_and_stream - device_info file does not exist or there is improperly formatted data")

    def update_webapp_with_new_details(self, ip_address, macaddress, serverport):
        with open(os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")) as unique_ids_file:
            unique_ids_file_response = json.load(unique_ids_file)

        device_unique_id = unique_ids_file_response["device_id"]
        api_bearer_key = unique_ids_file_response["api_token"]

        api_header = CaseInsensitiveDict()
        api_header["Authorization"] = f"Basic {device_unique_id}:{api_bearer_key}"
        api_header['Content-Type'] = 'application/json'
        updated_data = [{"IP": ip_address, "ServerPort": str(serverport), "MacAddress": macaddress}]

        print(">>> connect_and_stream - PostNewInputRelayRequestUpdate sending: " + str(updated_data))

        try:
            response = requests.post(self.post_input_relay_request_update_api, headers=api_header,
                                     data=json.dumps(updated_data))
        except Exception as api_error:
            print(">>> connect_and_stream - API Error: " + str(api_error))
        else:
            print(">>> connect_and_stream - PostNewInputRelayRequestUpdate response : ", response.status_code)
            print(">>> connect_and_stream - PostNewInputRelayRequestUpdate response text : ", response.text)

# Comment out the function when testing from main.py

# def start_thread():
#    if __name__ == "__main__":
#        connect_and_stream_instance = ConnectAndStream(device_mac="0008DC21DDF0")
#        # enter hardcoded MAC  and enter sped in milliseconds to query data from the device
#        connect_and_stream_instance.start()
#
#
# start_thread()
