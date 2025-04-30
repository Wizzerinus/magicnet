__all__ = ["AsyncIOSocketTransport"]

import asyncio
from typing import TYPE_CHECKING, cast

from magicnet.core.connection import ConnectionHandle
from magicnet.core.transport_handler import TransportHandler
from magicnet.util.messenger import StandardEvents

if TYPE_CHECKING:
    from magicnet.batteries.asyncio_network_manager import AsyncIONetworkManager


class AsyncIOSocketTransport(TransportHandler["AsyncIONetworkManager"]):
    """
    AsyncIOSocketTransport is used to communicate between two applications
    using the AsyncIO TCP sockets. Support for UDP and Unix sockets is planned.

    Note: this transport type will only work properly with AsyncIONetworkManager.
    """

    def send(self, connection: ConnectionHandle, dg: bytes) -> None:
        writer = cast(asyncio.StreamWriter, connection.connection_data)
        writer.write(len(dg).to_bytes(2, "big"))
        writer.write(dg)
        self.manager.spawn_task(writer.drain())

    def connect(self, host: str | None = None, port: int | None = None, *more: object) -> None:
        assert host is not None and port is not None
        self.manager.spawn_task(self.client_connection(host, port))

    async def client_connection(self, host: str, port: int):
        reader, writer = await asyncio.open_connection(host, port)
        await self.srv_callback(reader, writer, from_client=True)

    def open_server(self, host: str | None = None, port: int | None = None, *more: object) -> None:
        assert host is not None and port is not None
        self.manager.spawn_task(self.open_server_async(host, port))

    async def open_server_async(self, host: str, port: int):
        self.emit(StandardEvents.INFO, f"Server opened! Port: {port}")
        await asyncio.start_server(self.srv_callback, host, port)

    async def srv_callback(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        from_client: bool = False,
    ):
        self.emit(StandardEvents.INFO, "Client connection opened!")
        conn = ConnectionHandle(self, writer)
        if not from_client:
            self.send_motd(conn)
        while not reader.at_eof():
            try:
                bytelen = int.from_bytes(await reader.readexactly(2), byteorder="big")
                msg = await reader.readexactly(bytelen)
            except (asyncio.IncompleteReadError, ConnectionError):
                self.emit(StandardEvents.INFO, "AsyncIO connection closed!")
                break
            self.datagram_received(conn, msg)
        writer.close()
        conn.destroy()

    def before_disconnect(self, handle: ConnectionHandle) -> None:
        handle.connection_data.close()
