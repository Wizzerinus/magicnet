import asyncio
import dataclasses
import sys

from c_network_objects import c_common
from magicnet.batteries.asyncio_network_manager import AsyncIONetworkManager
from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.netobjects.network_field import NetworkField
from magicnet.netobjects.network_object import NetworkObject


@dataclasses.dataclass
class NetworkNumberClient(NetworkObject):
    network_name = "one-number"
    object_role = 0
    all_objects = []

    value: int = dataclasses.field(init=False, default=0)

    @classmethod
    def print_all(cls):
        if cls.all_objects:
            print("Current values:", " ".join(str(x.value) for x in cls.all_objects))

    def net_create(self):
        self.all_objects.append(self)
        self.print_all()

    def net_delete(self):
        self.all_objects.remove(self)
        self.print_all()

    @NetworkField
    def set_current_value(self, value):
        print(f"Value change: {self.value} -> {value}")
        self.value = value
        self.print_all()


manager = AsyncIONetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("client", c_common.transport),
    shutdown_on_disconnect=True,
    object_signature_filenames=c_common.signature_filenames,
    # debug_mode=True,
)
manager.object_registry.register_object(NetworkNumberClient)
cl_logger = manager.create_child(LoggerNode, prefix="asynciosocket.client")


async def read_loop():
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await manager.loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await manager.loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, manager.loop)
    print("trying to connect...")
    handle = await manager.wait_for_connection()
    print("connected")
    writer.write(
        b"Successfully connected! Our UUID is "
        + str(handle.uuid).encode("utf-8")
        + b"\n"
    )
    await writer.drain()
    manager.object_manager.request_visible_objects()

    while True:
        writer.write(b"Enter operation (either NEW [value] or ADD [number] [value]:\n")
        await writer.drain()
        operation = (await reader.readuntil()).decode("utf-8").strip()

        op_name, *args = operation.upper().split()
        args = list(map(int, args))
        if op_name == "NEW":
            obj = NetworkNumberClient(manager)
            obj.send_message("set_init_value", args)
            obj.request_generate()
        elif op_name == "ADD":
            try:
                obj = NetworkNumberClient.all_objects[args[0]]
                obj.send_message("add_value", [args[1]])
            except IndexError:
                writer.write(b"Bad arguments\n")
                await writer.drain()
        else:
            writer.write(b"Unknown operation\n")
            await writer.drain()


if __name__ == "__main__":
    manager.spawn_task(read_loop())
    manager.open_connection(server=("127.0.0.1", 5001))
