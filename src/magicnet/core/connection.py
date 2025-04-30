__all__ = ["ConnectionHandle"]

import dataclasses
from typing import TYPE_CHECKING, Annotated, Any, TypeVar
from uuid import UUID, uuid4

from magicnet.core import errors
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.protocol.protocol_globals import StandardDCReasons, StandardMessageTypes
from magicnet.util.messenger import StandardEvents
from magicnet.util.typechecking.magicnet_typechecker import check_type

if TYPE_CHECKING:
    from magicnet.core.transport_handler import TransportHandler


X = TypeVar("X")


@dataclasses.dataclass
class ConnectionHandle:
    """
    ConnectionHandle is an abstraction over a connection in the network.
    """

    transport: "TransportHandler[Any]" = dataclasses.field(repr=False)
    """The transport handler the connection belongs to"""
    connection_data: Any = dataclasses.field(repr=False)
    """Data used by the transport to identify the connection, i.e. socket handle"""
    uuid: UUID = dataclasses.field(default_factory=uuid4)
    activated: bool = False
    destroyed: bool = False
    context: dict[str, Any] = dataclasses.field(default_factory=dict)
    """Data used by the application to store data persistent for this connection"""
    shared_parameters: dict[str, Any] = dataclasses.field(default_factory=dict)
    """Same as context, but will be more or less the same on both sides"""

    def activate(self):
        if self.activated:
            return
        self.activated = True
        self.transport.manage_handle(self)
        self.transport.emit(MNEvents.HANDLE_ACTIVATED, self)

    def send_disconnect(self, reason: int, detail: str | None = None):
        msg = NetMessage(StandardMessageTypes.DISCONNECT, (reason, detail), destination=self)
        self.transport.manager.send_message(msg)
        self.destroy()

    def destroy(self):
        if self.destroyed:
            return
        self.destroyed = True
        self.transport.emit(MNEvents.HANDLE_DESTROYED, self)
        self.transport.destroy_handle(self)

    def set_shared_parameter(self, name: str, value: Any):
        self.shared_parameters[name] = value
        msg = NetMessage(StandardMessageTypes.SHARED_PARAMETER, (name, value), destination=self)
        self.transport.manager.send_message(msg)

    def get_shared_parameter(
        self, name: str, typehint: type[X] | Annotated[type[X], ...], *, disconnect: bool = False
    ) -> tuple[bool, X | None]:
        try:
            value = self.shared_parameters[name]
            check_type(value, typehint)
        except (KeyError, errors.DataValidationError):
            # This can happen, for example, when the user clears the parameter
            # (even if it is usually set). This may be rejected by a middleware,
            # but still possible if the middleware is bugged/etc,
            # so we can't rely on it
            if disconnect:
                self.send_disconnect(
                    StandardDCReasons.BROKEN_INVARIANT,
                    f"Shared parameter {name} is not set",
                )
            else:
                self.transport.emit(
                    StandardEvents.WARNING,
                    f"Unable to read the shared parameter {name} from {self.uuid}",
                )

            return False, None

        return True, value
