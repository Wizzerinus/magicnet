__all__ = ["ConnectionHandle"]

import dataclasses
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from magicnet.core.net_globals import MNEvents
from magicnet.protocol.protocol_globals import StandardMessageTypes

if TYPE_CHECKING:
    from magicnet.core.transport_handler import TransportHandler


@dataclasses.dataclass
class ConnectionHandle:
    """
    ConnectionHandle is an abstraction over a connection in the network.
    """

    transport: "TransportHandler" = dataclasses.field(repr=False)
    """The transport handler the connection belongs to"""
    connection_data: Any = dataclasses.field(repr=False)
    """Data used by the transport to identify the connection, i.e. socket handle"""
    uuid: uuid4 = dataclasses.field(default_factory=uuid4)
    activated: bool = False
    destroyed: bool = False
    context: dict = dataclasses.field(default_factory=dict)
    """Data used by the application to store data persistent for this connection"""

    def activate(self):
        if self.activated:
            return
        self.activated = True
        self.transport.manage_handle(self)
        self.transport.emit(MNEvents.HANDLE_ACTIVATED, self)

    def send_disconnect(self, reason: int, detail: str = None):
        # prevent circular import
        from magicnet.core.net_message import NetMessage

        msg = NetMessage(
            StandardMessageTypes.DISCONNECT, (reason, detail), destination=self
        )
        self.transport.manager.send_message(msg)
        self.destroy()

    def destroy(self):
        if self.destroyed:
            return
        self.destroyed = True
        self.transport.emit(MNEvents.HANDLE_DESTROYED, self)
        self.transport.destroy_handle(self)
