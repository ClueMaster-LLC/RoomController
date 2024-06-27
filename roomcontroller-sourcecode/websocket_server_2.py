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
auth_token = "YOUR_SECRET_BEARER_TOKEN"


async def authenticate(websocket, path):
    try:
        auth_header = websocket.request_headers.get('Authorization')
        if auth_header is None or not auth_header.startswith('Bearer '):
            await websocket.close(code=4001, reason="Missing or invalid token")
            return False

        token = auth_header.split(' ')[1]
        if token != auth_token:
            await websocket.close(code=4001, reason="Unauthorized")
            return False

        return True
    except Exception as e:
        print(f"Authentication error: {e}")
        await websocket.close(code=4001, reason="Error in authentication")
        return False


async def handler(websocket, path):
    if not await authenticate(websocket, path):
        return

    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # Here we can handle incoming messages if needed
            pass
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        connected_clients.remove(websocket)


async def send_command_to_all_clients(command, media_file=None):
    if connected_clients:
        message = {"command": command}
        if media_file:
            message["media_file"] = media_file
        message_json = json.dumps(message)
        await asyncio.wait([client.send(message_json) for client in connected_clients])


async def main():
    async with websockets.serve(handler, "192.168.1.16", 8765):
        while True:
            # command = input("Enter command (play/pause) and media file if needed (play media.mp4): ")
            command = "play"
            print(f'{command}')
            time.sleep(1)
            parts = command.split()
            if len(parts) > 1:
                command, media_file = parts[0], parts[1]
                await send_command_to_all_clients(command, media_file)
            else:
                await send_command_to_all_clients(parts[0])


# if __name__ == "__main__":
#     asyncio.run(main())


class WebsocketServer:
    def __init__(self):
        super(WebsocketServer, self).__init__()
        asyncio.run(main())
