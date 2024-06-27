import asyncio
import time

import websockets
import json
import os
import hashlib

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

connected_clients = set()


async def handler(websocket, path):
    # Register the client
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # Here we can handle incoming messages if needed
            pass
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        # Unregister the client
        connected_clients.remove(websocket)


async def send_command_to_all_clients(command):
    if connected_clients:
        message = json.dumps({"command": command})
        await asyncio.wait([client.send(message) for client in connected_clients])


async def main():
    async with websockets.serve(handler, "192.168.1.26", 8765):
        while True:
            # command = input("Enter command to synchronize video (play/pause): ")
            command = "play"
            print(command)
            time.sleep(1)
            await send_command_to_all_clients(command)


# if __name__ == "__main__":
#     asyncio.run(main())


class WebsocketServer:
    def __init__(self):
        super(WebsocketServer, self).__init__()
        asyncio.run(main())
