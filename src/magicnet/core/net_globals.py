__all__ = ["MNEvents", "MNMathTargets"]

from enum import Enum, auto


class MNEvents(Enum):
    """
    Standard events that can be emitted by the MagicNet's networking functionality,
    in addition to the ones that can be emitted by the messenger tree itself.
    """

    DATAGRAM_RECEIVED = auto()
    HANDLE_ACTIVATED = auto()
    HANDLE_DESTROYED = auto()
    MOTD_SET = auto()
    BEFORE_LAUNCH = auto()
    BEFORE_SHUTDOWN = auto()
    DISCONNECT = auto()
    BAD_NETWORK_OBJECT_CALL = auto()


class MNMathTargets(Enum):
    """
    Standard math targets that can be used by the MagicNet's networking functionality,
    in addition to the ones that can be used by the messenger tree itself.
    """

    MSG_SEND = auto()
    MSG_RECV = auto()
    BYTE_SEND = auto()
    BYTE_RECV = auto()
    VISIBLE_OBJECTS = auto()
    FIELD_CALL_ALLOWED = auto()
