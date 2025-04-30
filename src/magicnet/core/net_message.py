__all__ = ["NetMessage", "standard_range", "client_repo_range"]

import dataclasses
from typing import TYPE_CHECKING, Any, Generic

from typing_extensions import TypeVarTuple, Unpack

from magicnet.core import errors
from magicnet.util.messenger import StandardEvents

if TYPE_CHECKING:
    from magicnet.core.connection import ConnectionHandle

Ts = TypeVarTuple("Ts")


@dataclasses.dataclass
class NetMessage(Generic[Unpack[Ts]]):
    message_type: int
    """
    The standard message types are 6-bit (from 0 to 63).
    Those will be processed by the MagicNet core.
    Custom types can be any 64-bit integers above 63.
    Those will be processed by the application logic.
    """
    parameters: tuple[Unpack[Ts]] = ()  # pyright: ignore[reportAssignmentType]
    """
    List of parameters of the message. Each message type
    has its own signature defined in the class.
    """
    sent_from: "ConnectionHandle | None" = None
    """
    Handle of the sender. Usually this should not be edited.
    """
    destination: "ConnectionHandle | None" = None
    """
    The connection to which this message should be routed.
    This cannot be overridden by the router in any way.
    If this is undesired, the application-specific router may use routing_data
    to determine the destination.
    """
    routing_data: Any = None
    """
    This is a field for the application logic to use, if a custom routing logic
    is required. It will not be delivered in the message itself.
    """

    @property
    def value(self):
        return self.message_type, self.parameters

    @classmethod
    def from_value(cls, value: tuple[int, tuple[Unpack[Ts]]]):
        # sent_from will be populated later
        return cls(message_type=value[0], parameters=value[1])

    def disconnect_sender(self, reason: int, detail: str | None = None):
        if not self.sent_from:
            raise errors.SenderNotSet(self)
        self.sent_from.transport.emit(
            StandardEvents.WARNING, f"Disconnecting sender {self.sent_from.uuid} for {reason=} {detail=}"
        )
        self.sent_from.send_disconnect(reason, detail)


standard_range = range(64)
client_repo_range = range(1, 128)
