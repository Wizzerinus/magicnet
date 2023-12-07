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

    CREATE_OBJECT = auto()
    """
    Requests the other side of the connection to create a network object.
    The object will bw owned by the user whose repository is provided
    as the owner parameter. If you want to create an object you own,
    provide the 'rp' shared parameter as the owner.
    Note that the object ID will be based on the creator's repository
    and not the owner's repository.

    The object will be created in some zone. By default, the zones
    don't do anything, unless the ZoneVisibilityMiddleware is used
    (or a custom in-house middleware with a similar purpose).

    The network object may have initial parameters. Those will be derived
    from the object's value itself.

    Parameters: [uint32 oid, uint16 type, uint32 owner,
                 uint32 zone, list[tuple[uint8, uint8, hashable]] params]
    """

    GENERATE_OBJECT = auto()
    """
    Requests the other side of the connection to generate a network object
    that exists on the current side of the connection.
    Usually called after CREATE_OBJECT.

    The initial parameters will be passed separately through calls to
    SET_OBJECT_FIELD, followed by OBJECT_GENERATE_DONE.

    Parameters: [uint64 oid, uint16 type, uint32 owner, uint32 zone]
    """

    REQUEST_DELETE_OBJECT = auto()
    """
    Requests the other side of the connection to destroy all copies
    of a network object. The object must be owned by the current app.

    Parameters: [uint64 oid]
    """

    DESTROY_OBJECT = auto()
    """
    Destroys an object. Usually happens after DELETE_OBJECT is sent.

    Parameters: [uint64 oid]
    """

    SET_OBJECT_FIELD = auto()
    """
    Calls a field method for a given object.

    Parameters: [uint64 oid, uint8 method, list[hashable] params]
    """

    OBJECT_GENERATE_DONE = auto()
    """
    Indicates that the object generation is finished.
    It is expected that the object exists by this point.

    Parameters: [uint64 oid]
    """

    REQUEST_VISIBLE_OBJECTS = auto()
    """
    This method is called at some point after the client connects to the server.
    For each object that the client should see, the server must reply
    with the standard generate procedure
    (GENERATE_OBJECT, zero or more SET_OBJECT_FIELD, then OBJECT_GENERATE_DONE).
    It is expected that the client unloads the object they do not see
    before this is called, if the infrastructure requires multiple calls to this.

    Parameters: []
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
    INVALID_OBJECT_TYPE = auto()
    """The client asked to create a network object with a non-existent type"""


mn_proto_version = 3
