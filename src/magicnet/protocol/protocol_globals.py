__all__ = ["StandardMessageTypes", "StandardDCReasons", "mn_proto_version"]

from enum import IntEnum, auto


class StandardMessageTypes(IntEnum):
    MOTD = auto()
    """
    MOTD message is sent by the server to declare that the connection is accepted.
    Any connection handle will send exactly one of MOTD and HELLO.

    Parameters: [string64 motd].
    """

    HELLO = auto()
    """
    HELLO message is sent after MOTD is received to initiate the connection.
    It does some basic checks, which should not be relied on,
    and are mostly to prevent accidental failures.

    Parameters: [uint16 proto_ver, bytestring64 hash].
    """

    DISCONNECT = auto()
    """
    DISCONNECT will be sent on any connection (client or server)
    before the connection is forcefully broken from that side.

    Parameters: [uint8 reason, string64 description | null]
    """

    SHUTDOWN = auto()
    """
    Sent when the other end of the connection is shut down
    (i.e. client disconnects or server is rebooted).

    Parameters: []
    """

    SHARED_PARAMETER = auto()
    """
    One side of the connection asks the other to set a shared parameter
    to some value. Unlike connection context, shared parameters are
    the same on both sides of the connection. Shared parameters can have
    any type (that can be encoded in json/msgpack), but the middleware
    may intercept a request if the type is wrong.

    Parameters: [string name, object value]
    """


class StandardDCReasons(IntEnum):
    HELLO_MULTIPLE = auto()
    """Multiple HELLO messages were sent"""
    HELLO_INVALID_PROTO_VER = auto()
    """The protocol version does not match the one of the server's"""
    HELLO_HASH_MISMATCH = auto()
    """The client hash does not match the one of the server's"""
    MESSAGE_BEFORE_HELLO = auto()
    """The client sent a disallowed message before handshake was established"""
    BROKEN_INVARIANT = auto()
    """One of the invariants enforced by MagicNetworking is not fulfilled"""


mn_proto_version = 2
