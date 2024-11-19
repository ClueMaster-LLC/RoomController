import threading
import time
import json
import os
import hashlib

import asyncio
import websockets
from websockets import WebSocketServerProtocol
import room_controller

clients = set()


# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")

connected_clients = set()

global WEBSOCKETSERVER_STOP
WEBSOCKETSERVER_STOP: bool = False


# master class
class WebsocketServer(threading.Thread):
    def __init__(self):
        super(WebsocketServer, self).__init__()

        self.global_device_unique_id = room_controller.GLOBAL_DEVICE_UNIQUE_ID

        self.server_url = room_controller.GLOBAL_IP
        # self.port = 8760

        # print(f'GLOBAL IP = {room_controller.GLOBAL_IP}')

        print(f">>> websocket_server - ***STARTUP COMPLETED***")
        asyncio.run(main(self.server_url))
        print(">>> websocket_server - **********  WEBSOCKET_SERVER THREAD SHUTTING DOWN  **********")


async def register(websocket: WebSocketServerProtocol):
    clients.add(websocket)
    print(f">>> websocket_server - Client {websocket.remote_address} connected")
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print(f">>> websocket_server - Client {websocket.remote_address} disconnected")


async def handle_command(websocket: WebSocketServerProtocol, message: str):
    # Split the command to handle individual or broadcast
    parts = message.split(maxsplit=1)
    command = parts[0]
    target = parts[1] if len(parts) > 1 else None

    if command == "broadcast":
        # Send to all clients
        if target:
            await asyncio.gather(*(client.send(target) for client in clients))
            print(f">>> websocket_server - Broadcasted message to all clients: {target}")
    elif command.startswith("sendto"):
        # Send to a specific client
        if target:
            address, msg = target.split(maxsplit=1)
            for client in clients:
                if str(client.remote_address) == address:
                    await client.send(msg)
                    print(f">>> websocket_server - Sent message to {address}: {msg}")
                    break
    else:
        print(f">>> websocket_server - Unknown command: {command}")


async def handler(websocket: WebSocketServerProtocol, path: str):
    await register(websocket)
    try:
        async for message in websocket:
            print(f">>> websocket_server - Received message from {websocket.remote_address}: {message}")
            await handle_command(websocket, message)
    except websockets.ConnectionClosed:
        print(f">>> websocket_server - Connection with {websocket.remote_address} closed")


async def main(server_url):
    server = await websockets.serve(handler, server_url, 8765)
    print(f">>> websocket_server - Server started on {server_url}:8765")
    await server.wait_closed()

# if __name__ == "__main__":
#     asyncio.run(main())


# class WebsocketServer:
#     def __init__(self):
#         super(WebsocketServer, self).__init__()
#         asyncio.run(main())
