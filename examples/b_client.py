import asyncio
import functools
import logging
import sys

import b_common
from magicnet.batteries.asyncio_network_manager import AsyncIONetworkManager
from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage

client = AsyncIONetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("client", b_common.transport),
    extras=b_common.extra_message_types,
    shutdown_on_disconnect=True,
)
cl_logger = client.create_child(LoggerNode, prefix="asynciosocket.client")
cl_logger.listen(MNEvents.MOTD_SET, functools.partial(cl_logger.log, logging.INFO))
cl_logger.listen(MNEvents.DISCONNECT, functools.partial(cl_logger.log, logging.WARNING))


async def read_loop():
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await client.loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await client.loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, client.loop)
    handle = await client.wait_for_connection()
    writer.write(
        b"Successfully connected! Our UUID is "
        + str(handle.uuid).encode("utf-8")
        + b"\n"
    )
    await writer.drain()

    writer.write(b"Enter your username: ")
    await writer.drain()
    name = (await reader.readuntil()).decode("utf-8").strip()
    msg = NetMessage(b_common.MSG_SET_NAME, (name,))
    client.send_message(msg)
    writer.write(b"Username successfully set!\n")
    await writer.drain()

    while True:
        text = (await reader.readuntil()).decode("utf-8").strip()
        msg = NetMessage(b_common.MSG_CUSTOM, (text,))
        client.send_message(msg)


client.spawn_task(read_loop())
client.open_connection(server=("127.0.0.1", 5000))
