__all__ = ["SingleAppTransport"]

import dataclasses
from typing import cast
from uuid import UUID, uuid4

from magicnet.core.connection import ConnectionHandle
from magicnet.core.network_manager import NetworkManager
from magicnet.core.transport_handler import TransportHandler
from magicnet.util.messenger import StandardEvents


@dataclasses.dataclass
class SingleAppTransport(TransportHandler):
    """
    SingleAppTransport is used to communicate between two applications
    launched in the same process. This can be used to simplify local development.
    """

    remote_nodes: list["SingleAppTransport"] = dataclasses.field(default_factory=list)
    handle_map: dict[UUID, ConnectionHandle] = dataclasses.field(default_factory=dict)

    def send(self, connection: ConnectionHandle, dg: bytes) -> None:
        for node in self.remote_nodes:
            handle_inverse = node.handle_map.get(connection.connection_data)
            if handle_inverse:
                node.datagram_received(handle_inverse, dg)
                return

        self.emit(StandardEvents.ERROR, "The opposite transport isn't defined!")
        return

    def connect(self, connection_data: NetworkManager | None = None, *more: object) -> None:
        assert connection_data is not None
        transport = cast(SingleAppTransport, connection_data.transport.transports[self.manager.role])
        self.remote_nodes.append(transport)
        transport.remote_nodes.append(self)
        handle = ConnectionHandle(self, uuid4())
        self.handle_map[handle.connection_data] = handle
        transport.handle_new_connection(handle)

    def handle_new_connection(self, handle: ConnectionHandle):
        server_handle = ConnectionHandle(self, handle.connection_data)
        self.handle_map[server_handle.connection_data] = server_handle
        self.send_motd(server_handle)

    def before_disconnect(self, handle: ConnectionHandle) -> None:
        self.handle_map.pop(handle.connection_data)

    def open_server(self, *args: object) -> None:
        # Deliberately unneeded
        pass

    def shutdown(self):
        # Deliberately unneeded
        pass
