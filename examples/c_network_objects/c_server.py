import dataclasses
import functools

from c_network_objects import c_common
from magicnet.batteries.asyncio_network_manager import AsyncIONetworkManager
from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.core.errors import DataValidationError
from magicnet.core.net_globals import MNEvents
from magicnet.netobjects.network_field import NetworkField
from magicnet.netobjects.network_object import NetworkObject
from magicnet.protocol import network_types
from magicnet.protocol.network_typechecker import check_type
from magicnet.util.messenger import StandardEvents


@dataclasses.dataclass
class NetworkNumberServer(NetworkObject):
    network_name = "one-number"
    object_role = 1
    value: int = dataclasses.field(init=False, default=0)

    def net_create(self):
        print("net_create called")

    def net_delete(self):
        pass

    @NetworkField
    def set_init_value(self, value: network_types.int32):
        print(f"New number with value: {value}")
        self.value = value
        self.send_message("set_current_value", [self.value])

    @NetworkField
    def add_value(self, value: network_types.int32):
        try:
            check_type(value + self.value, network_types.int32)
        except DataValidationError:
            self.emit(
                StandardEvents.WARNING, f"Integer overflow: {value} + {self.value}"
            )
            return

        print(f"after add_value: {self.value}+{value} -> {self.value + value}")
        self.value += value
        self.send_message("set_current_value", [self.value])


manager = AsyncIONetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("server", c_common.transport),
    motd="An example native host",
    object_signature_filenames=c_common.signature_filenames,
    # debug_mode=True,
)
manager.object_registry.register_object(NetworkNumberServer)
sr_logger = manager.create_child(LoggerNode, prefix="asynciosocket.server")
sr_logger.listen(MNEvents.HANDLE_ACTIVATED, functools.partial(print, "server handle:"))
sr_logger.listen(MNEvents.HANDLE_DESTROYED, functools.partial(print, "handle died:"))

if __name__ == "__main__":
    manager.open_server(client=("127.0.0.1", 5001))
