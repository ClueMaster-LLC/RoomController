import asyncio
import logging
from signalr_async.netcore import Hub, Client
from signalr_async.netcore.protocols import MessagePackProtocol, JsonProtocol
from typing import Any, Dict, List

class MyHub(Hub):
    async def on_connect(self, connection_id: str) -> None:
        """Will be awaited after connection established"""
        print("Connected ID: " + str(connection_id))

    async def on_disconnect(self) -> None:
        """Will be awaited after client disconnection"""
        return print("Disconnected")

    def send_message(self, x: str, y: str) -> None:
        """Invoked by server synchronously on (event_one)"""
        return self.invoke('SendMessage', x, y)

    async def send_message_async(self, x: str, y: str) -> None:
        """Invoked by server asynchronously on (event_two)"""
        return await self.invoke('SendMessage', x, y)

    async def on_message(message: List[Dict[str, Any]]) -> None:
        print(f'Received message: {message}')
    
##    async def on_receive(self) -> None:
##        #receive new chat messages from the hub
##        await self.invoke("ReceiveMessage", print)


hub = MyHub("chathub")
##hub = "chatHub"

@hub.on("ReceiveMessage")
async def ReceiveMessage(x: str, z: str,) -> None:
    print(f'User: {x} , Message: {z}')

@hub.on
async def multi_event(z: int) -> None:
    pass


for i in range(10):
    hub.on(f"event_{i}", multi_event)


async def main():
    token = "F48C-5064-6347:c156e961919141723e5cb21c01647838cf5fc7f39b0a1bb31c9f4c1daeb4e348"
    headers = {"Authorization": f"Bearer {token}"}
    async with Client(
        "https://devapi.cluemaster.io/",
        hub,
        connection_options={
            "http_client_options": {"headers": headers},
            "ws_client_options": {"headers": headers, "timeout": 5.0},
##            "protocol": MessagePackProtocol(),
            "protocol": JsonProtocol(),
            "logger": logging.DEBUG,
        },
    ) as client:
        #await hub.on_message()
        await hub.send_message_async("DEVICE1","Connected data sending")

        message = None
        username = "Robert"

        while message != "exit()":
            message = input(">> ")
            if message is not None and message != "" and message != "exit()":
                await hub.send_message("Robert", message)
                await hub.send_message_async("Robert", message)


asyncio.run(main())
print("test")
