__all__ = ["SingleAppTransport"]

import dataclasses
from typing import cast
from uuid import uuid4

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

    other_transport: "SingleAppTransport" = None
    handle_map: dict[uuid4, ConnectionHandle] = dataclasses.field(default_factory=dict)

    def send(self, connection: ConnectionHandle, dg: bytes) -> None:
        if not self.other_transport:
            self.emit(StandardEvents.ERROR, "The opposite transport isn't defined!")
            return

        handle_inverse = self.other_transport.handle_map[connection.connection_data]
        self.other_transport.datagram_received(handle_inverse, dg)

    def connect(self, connection_data: NetworkManager) -> None:
        transport = connection_data.transport.transports[self.manager.role]
        self.other_transport = cast(SingleAppTransport, transport)
        self.other_transport.other_transport = self
        handle = ConnectionHandle(self, uuid4())
        self.handle_map[handle.connection_data] = handle
        self.other_transport.handle_new_connection(handle)

    def handle_new_connection(self, handle: ConnectionHandle):
        server_handle = ConnectionHandle(self, handle.connection_data)
        self.handle_map[server_handle.connection_data] = server_handle
        self.send_motd(server_handle)

    def before_disconnect(self, handle: ConnectionHandle) -> None:
        self.handle_map.pop(handle.connection_data)

    def open_server(self) -> None:
        # Deliberately unneeded
        pass

    def shutdown(self):
        # Deliberately unneeded
        pass
