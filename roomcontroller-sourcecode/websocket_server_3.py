import asyncio
import websockets
from websockets import WebSocketServerProtocol

clients = set()


async def register(websocket: WebSocketServerProtocol):
    clients.add(websocket)
    print(f"Client {websocket.remote_address} connected")
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print(f"Client {websocket.remote_address} disconnected")


async def handle_command(websocket: WebSocketServerProtocol, message: str):
    # Split the command to handle individual or broadcast
    parts = message.split(maxsplit=1)
    command = parts[0]
    target = parts[1] if len(parts) > 1 else None

    if command == "broadcast":
        # Send to all clients
        if target:
            await asyncio.gather(*(client.send(target) for client in clients))
            print(f"Broadcasted message to all clients: {target}")
    elif command.startswith("sendto"):
        # Send to a specific client
        if target:
            address, msg = target.split(maxsplit=1)
            for client in clients:
                if str(client.remote_address) == address:
                    await client.send(msg)
                    print(f"Sent message to {address}: {msg}")
                    break
    else:
        print(f"Unknown command: {command}")


async def handler(websocket: WebSocketServerProtocol, path: str):
    await register(websocket)
    try:
        async for message in websocket:
            print(f"Received message from {websocket.remote_address}: {message}")
            await handle_command(websocket, message)
    except websockets.ConnectionClosed:
        print(f"Connection with {websocket.remote_address} closed")


async def main():
    server = await websockets.serve(handler, "localhost", 8765)
    print("Server started")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
