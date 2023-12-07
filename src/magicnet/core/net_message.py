__all__ = ["NetMessage", "standard_range", "client_repo_range"]

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magicnet.core.connection import ConnectionHandle


@dataclasses.dataclass
class NetMessage:
    message_type: int
    """
    The standard message types are 6-bit (from 0 to 63).
    Those will be processed by the MagicNet core.
    Custom types can be any 64-bit integers above 63.
    Those will be processed by the application logic.
    """
    parameters: list | tuple = ()
    """
    List of parameters of the message. Each message type
    has its own signature defined in the class.
    """
    sent_from: "ConnectionHandle" = None
    """
    Handle of the sender. Usually this should not be edited.
    """
    destination: "ConnectionHandle" = None
    """
    Existence of this field is a bit misleading, it usually only matters
    for the callback set on HandleFilter (or TransportManager).
    The default HandleFilter will be only sending messages
    to the destination if one is set, though.
    """
    f_destination: "ConnectionHandle" = None
    """
    This is similar to destination, except it cannot be overwritten
    by the HandleFilter. If this is set the message is always
    going to this handle and nothing else, regardless of what
    the filter says (this is for internal messaging purposes).
    This shouldn't be used except in the internal code of the library.
    """

    @property
    def value(self):
        return self.message_type, self.parameters

    @classmethod
    def from_value(cls, value):
        # sent_from will be populated later
        return cls(message_type=value[0], parameters=value[1])

    def disconnect_sender(self, reason: int, detail: str = None):
        self.sent_from.send_disconnect(reason, detail)


standard_range = range(64)
client_repo_range = range(1, 128)
