import threading
import time
import json
import os
import asyncio
import websockets
import room_controller


# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

# global WEBSOCKETSERVER_STOP
# WEBSOCKETSERVER_STOP: bool = False


# master class
class WebsocketServer(threading.Thread):
    def __init__(self):
        super(WebsocketServer, self).__init__()

        self.global_device_unique_id = room_controller.GLOBAL_DEVICE_UNIQUE_ID

        self.server_url = room_controller.GLOBAL_IP
        # self.port = 8760

        print(f">>> websocket_server - ***STARTUP COMPLETED***")
        asyncio.run(main(self.server_url))
        print(">>> websocket_server - **********  WEBSOCKET_SERVER THREAD SHUTTING DOWN  **********")


connected_clients = {}
auth_token = "YOUR_SECRET_BEARER_TOKEN"


async def authenticate(websocket):
    auth_header = websocket.request_headers.get('Authorization')
    if auth_header is None or not auth_header.startswith('Bearer '):
        await websocket.close(code=4001, reason="Missing or invalid token")
        return False

    token = auth_header.split(' ')[1]
    if token != auth_token:
        await websocket.close(code=4001, reason="Unauthorized")
        return False

    return True


async def handler(websocket, path):
    if not await authenticate(websocket):
        return

    client_id = await websocket.recv()
    connected_clients[client_id] = websocket
    print(f">>> websocket_server - Client {client_id} connected.")

    try:
        async for message in websocket:
            # Handle incoming messages from clients if needed
            pass
    except websockets.exceptions.ConnectionClosed:
        print(f">>> websocket_server - Client {client_id} disconnected.")
    finally:
        del connected_clients[client_id]


async def send_command_to_all_clients(command, media_file=None):
    message = {"command": command}
    if media_file:
        message["media_file"] = media_file
    message_json = json.dumps(message)

    if connected_clients:
        # await asyncio.wait([client.send(message_json) for client in connected_clients.values()])
        await asyncio.gather(*(client.send(message_json) for client in connected_clients.values()))
        print(f">>> websocket_server - Broadcast message to all clients")


async def send_command_to_specific_client(client_id, command, media_file=None):
    if client_id in connected_clients:
        message = {"command": command}
        if media_file:
            message["media_file"] = media_file
        message_json = json.dumps(message)
        await connected_clients[client_id].send(message_json)


async def periodic_task():
    while True:
        try:
            for client_id in connected_clients.keys():
                time.sleep(5)
                await send_command_to_specific_client(client_id, "play", "77-20240801065957-HTVLDL.m4v")
                print(f">>> websocket_server - Send to {client_id}: Play Video 001.mpg")
                time.sleep(1)
                # await send_command_to_specific_client(client_id, "pause")
                # print(f">>> websocket_server - Send to {client_id}: pause")
                # await send_command_to_all_clients("play", "001.mpg")
            await asyncio.sleep(15)
        except Exception as e:
            print(f">>> websocket_server - Error: {e}")
            time.sleep(5)


async def main(server_url):
    server = await websockets.serve(handler, server_url, 8765, ping_interval=10)
    print(f">>> websocket_server - Server started on {server_url}:8765")
    await periodic_task()  # Run periodic task in the background
    await server.wait_closed()



