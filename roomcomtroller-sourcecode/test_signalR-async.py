import asyncio
from signalr_async.netcore import Hub, Client
from signalr_async.netcore.protocols import MessagePackProtocol, JsonProtocol


class MyHub(Hub):
    async def on_connect(self, connection_id: str) -> None:
        """Will be awaited after connection established"""

    async def on_disconnect(self) -> None:
        """Will be awaited after client disconnection"""

    def on_event_one(self, x: bool, y: str) -> None:
        """Invoked by server synchronously on (event_one)"""

    async def on_event_two(self, x: bool, y: str) -> None:
        """Invoked by server asynchronously on (event_two)"""

    async def get_something(self) -> bool:
        """Invoke (method) on server"""
        return await self.invoke("Send2", "Hello Tesing", 2)


hub = MyHub("chatHub")
##hub = "chatHub"

@hub.on("event_three")
async def three(z: int) -> None:
    pass


@hub.on
async def event_four(z: int) -> None:
    pass


async def multi_event(z: int) -> None:
    pass


for i in range(10):
    hub.on(f"event_{i}", multi_event)


async def main():
    token = "F48C-5064-6347:c156e961919141723e5cb21c01647838cf5fc7f39b0a1bb31c9f4c1daeb4e348"
    headers = {"Authorization": f"Bearer {token}"}
    async with Client(
        "https://devapi.cluemaster.io",
        hub,
        connection_options={
            "http_client_options": {"headers": headers},
            "ws_client_options": {"headers": headers, "timeout": 1.0},
##            "protocol": MessagePackProtocol(),
            "protocol": JsonProtocol(),
##            "logger": logging.Logger(),
        },
    ) as client:
        return await hub.get_something()


asyncio.run(main())
