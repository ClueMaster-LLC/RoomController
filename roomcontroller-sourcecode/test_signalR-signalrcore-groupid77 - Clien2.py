import logging
import sys
import time

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
device_mac = '0008DC225455'
#server_url = f"https://cluemaster-signalr-win.azurewebsites.net/chathub?{device_mac}"
##server_url = f"wss://comhub.cluemaster.io/chathub?serialnumber={device_mac}"
#server_url = f"https://comhub.cluemaster.io/chathub?{device_mac}"
server_url = f"https://comhub.cluemaster.io/chathub"
print(server_url)

#token = "F48C-5064-6347:c156e961919141723e5cb21c01647838cf5fc7f39b0a1bb31c9f4c1daeb4e348"
#headers = {"Authorization": f"Bearer {token}"}
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
hub_connection = HubConnectionBuilder()\
    .with_url(server_url, options={
                "verify_ssl": True,
                "skip_negotiation": False,
 #               "http_client_options": {"headers": headers, "timeout": 5.0},
 #               "ws_client_options": {"headers": headers, "timeout": 5.0},
                #"user": str(device_mac)
        }) \
    .configure_logging(logging.ERROR, socket_trace=True, handler=handler) \
    .with_automatic_reconnect({
            "type": "raw",
            "keep_alive_interval": 10,
            "intervals": [1, 3, 5, 6, 7, 87, 3]
        })\
    .build()

# hub_connection.on_open(lambda: print("connection opened and handshake received ready to send messages"))
hub_connection.on_open(lambda: (hub_connection.send('AddToGroup', [str(room_id)]),
                                hub_connection.send('AddToGroup', [str(device_mac)]),
                                     print(f">>> connect_and_stream - {device_mac} - signalR handshake "
                                           f"received. Ready to send/receive messages.")))
hub_connection.on_close(lambda: print("connection closed"))
hub_connection.on_error(lambda data: print(f"An exception was thrown closed{data.error}"))
hub_connection.on_reconnect(lambda: print("re-connected"))
hub_connection.on('syncdata', (lambda data: print(f"syncdata command received: {data}")))
hub_connection.on("relay_on", (lambda data: print(f"RELAY ON {data}")))
hub_connection.on('relay_off', (lambda data: print(f"RELAY OFF {data}")))
##hub_connection.on(str(device_mac), print)
##hub_connection.on(str(room_id), (lambda data: print(f"GROUP ID DATA {data}")))
##hub_connection.on('relay_off_TEST', (lambda data: print(f"TEST RELAY OFF {data}")))
hub_connection.on('ReceiveMessage', (lambda data: print(f"Message received: {data}")))


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
