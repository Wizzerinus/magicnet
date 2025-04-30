__all__ = ["message_processors"]

from typing import Final

from magicnet.protocol.processors import data, handshake, network_objects
from magicnet.protocol.protocol_globals import StandardMessageTypes

message_processors: Final = {
    StandardMessageTypes.MOTD: handshake.MsgMotd,
    StandardMessageTypes.HELLO: handshake.MsgHello,
    StandardMessageTypes.DISCONNECT: handshake.MsgDisconnect,
    StandardMessageTypes.SHUTDOWN: handshake.MsgShutdown,
    StandardMessageTypes.SHARED_PARAMETER: data.MsgSharedParameter,
    StandardMessageTypes.CREATE_OBJECT: network_objects.MsgCreateObject,
    StandardMessageTypes.GENERATE_OBJECT: network_objects.MsgGenerateObject,
    StandardMessageTypes.SET_OBJECT_FIELD: network_objects.MsgSetObjectField,
    StandardMessageTypes.OBJECT_GENERATE_DONE: network_objects.MsgObjectGenerateDone,
    StandardMessageTypes.REQUEST_DELETE_OBJECT: network_objects.MsgDeleteObject,
    StandardMessageTypes.DESTROY_OBJECT: network_objects.MsgDestroyObject,
    StandardMessageTypes.REQUEST_VISIBLE_OBJECTS: network_objects.MsgRequestVisible,
}
