import logging
import sys
import time
import requests

import signalrcore.hub.base_hub_connection
from signalrcore.hub_connection_builder import HubConnectionBuilder
from signalrcore.protocol.messagepack_protocol import MessagePackHubProtocol

global signalr_status
signalr_status = None
room_id = 77
signalr_connected = None

def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value


##server_url = input_with_default('Enter your server url(default: {0}): ', "https://devapi.cluemaster.io/chathub")
##username = input_with_default('Enter your username (default: {0}): ', "robert")
##server_url = "https://devapi.cluemaster.io/chathub"
device_mac = '0008DC22545X'
#server_url = f"https://cluemaster-signalr-win.azurewebsites.net/chathub?{device_mac}"
##server_url = f"https://comhub.cluemaster.io/chathub?serialnumber={device_mac}"
#server_url = f"https://comhub.cluemaster.io/chathub?{device_mac}"



token = "F48C-5064-6347_f44442f10275efe965cf815c2de7f18c44446eee422ba7f80d6a768ca3eee11b"
headers = {"Authorization": f"Bearer {token}"}

hard_token = '1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt'
headers2 = {"Authorization": f"{token}"}
access_token = 'access_token=1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt',

server_url = f"wss://dev-comhub.cluemaster.io/chathub?access_token={token}"
print(server_url)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
hub_connection = HubConnectionBuilder()\
    .with_url(server_url, options={
                "verify_ssl": True,
                "skip_negotiation": False,
                "http_client_options": {"headers": access_token, "timeout": 5.0},
                "ws_client_options": {"headers": access_token, "timeout": 5.0}
##                "serialnumber": str(device_mac)
        }) \
    .configure_logging(logging.DEBUG, socket_trace=True, handler=handler) \
    .with_hub_protocol(MessagePackHubProtocol()) \
    .with_automatic_reconnect({
            "type": "raw",
            "keep_alive_interval": 10,
            "intervals": [1, 3, 5, 6, 7, 87, 3]
        })\
    .build()

##                "access_token_factory": lambda: '1212-1212-1212_www5e9eb82c38bffe63233e6084c08240ttt',
##hub_connection.on_open(lambda: print("connection opened and handshake received ready to send messages"))
hub_connection.on_open(lambda: (hub_connection.send('AddToGroup', [str(room_id)]),
                                     print(f">>> connect_and_stream - {device_mac} - signalR handshake "
                                           f"received. Ready to send/receive messages. Also joined group {room_id}")))
hub_connection.on_close(lambda: print("connection closed"))
hub_connection.on_error(lambda data: print(f"An exception was thrown closed{data.error}"))
hub_connection.on_reconnect(lambda: print("re-connected"))
hub_connection.on('syncdata', (lambda data: print(f"syncdata command received: {data}")))
hub_connection.on("relay_on", (lambda data: print(f"RELAY ON {data}")))
hub_connection.on('relay_off', (lambda data: print(f"RELAY OFF {data}")))
hub_connection.on(str(device_mac), print)
hub_connection.on(str(room_id), (lambda data: print(f"GROUP ID DATA {data}")))
hub_connection.on('ReceiveMessage', (lambda data: print(f"syncdata command received: {data}")))

hub_connection.on('relay_off_TEST', (lambda data: print(f"TEST RELAY OFF {data}")))


try:
    hub_connection.start()
    print("SignalR Connection Started")
    for i in range(3, 0, -1):
        print(f'Starting in ... {i}')
        time.sleep(1)
##    hub_connection.send('AddToGroup', ["77"])
##    print(f'Joined signalR group # 77')
except Exception as e:
    print(e)


##hub_connection.start()
##
##while signalr_status is not True:
##    for i in range(15, -1, -1):
##        if signalr_status is True:
##            break
##        if i == 0:
##            print(f'>>> connect_and_stream - {device_mac} - Timeout exceeded. SignalR not connected.')
##            break
##        print(f'>>> connect_and_stream - {device_mac} - waiting for signalR handshake ... {i}')
##        time.sleep(1)
##    break
##else:
##    print(">>> connect_and_stream - signalr connected")
##
##def signalr_connected(self, status):
##    if self.status is True:
##        signalr_status = True
##    elif not self.status:
##        signalr_status = False



##while hub_connection.on:
##    print("hub is on")
message = ["1"]

##hub_connection.send('SyncRequestToRoom', message)
#print('SyncRequestToRoom', ["1"])
# Do login

##while message != "exit()":
##    message = input(">> ")
##    if message is not None and message != "" and message != "exit()":
##        hub_connection.send('SendMessage', [username, message])

#hub_connection.stop()

#sys.exit(0)

#.with_hub_protocol(MessagePackHubProtocol()) \
