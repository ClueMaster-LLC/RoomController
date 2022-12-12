import logging
import sys
import time
from signalrcore.hub_connection_builder import HubConnectionBuilder
#from signalrcore.protocol.messagepack_protocol import MessagePackHubProtocol


def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value


server_url = input_with_default('Enter your server url(default: {0}): ', "https://devapi.cluemaster.io/chathub")
username = input_with_default('Enter your username (default: {0}): ', "robert")
token = "F48C-5064-6347:c156e961919141723e5cb21c01647838cf5fc7f39b0a1bb31c9f4c1daeb4e348"
headers = {"Authorization": f"Bearer {token}"}
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
hub_connection = HubConnectionBuilder()\
    .with_url(server_url, options={
        "verify_ssl": True,
##        "http_client_options": {"headers": headers},
##        "ws_client_options": {"headers": headers, "timeout": 1.0},
        }) \
    .configure_logging(logging.ERROR, socket_trace=True, handler=handler) \
    .with_automatic_reconnect({
            "type": "raw",
            "keep_alive_interval": 10,
            "intervals": [1, 3, 5, 6, 7, 87, 3]
        })\
    .build()

hub_connection.on_open(lambda: print("connection opened and handshake received ready to send messages"))
hub_connection.on_close(lambda: print("connection closed"))
hub_connection.on_reconnect(lambda: print("re-connected"))
hub_connection.on("ReceiveMessage", print)

try:
    hub_connection.start()
    print("SignalR Connection Started")
    for i in range(5, 0, -1):
        print(f'Starting in ... {i}')
        time.sleep(1)
    hub_connection.send('AddToGroup', ["44"])
    print(f'Joined signalR group # 44')
except Exception as e:
    print(e)

##while hub_connection.on:
##    print("hub is on")
message = None

# Do login

##while message != "exit()":
##    message = input(">> ")
##    if message is not None and message != "" and message != "exit()":
##        hub_connection.send('SendMessage', [username, message])

##hub_connection.stop()

sys.exit(0)
#.with_hub_protocol(MessagePackHubProtocol())\
