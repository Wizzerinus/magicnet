__all__ = ["message_processors"]

from magicnet.protocol.processor_base import MessageProcessor
from magicnet.protocol.processors import data, handshake
from magicnet.protocol.protocol_globals import StandardMessageTypes

message_processors: dict[StandardMessageTypes, type[MessageProcessor]] = {
    StandardMessageTypes.MOTD: handshake.MsgMotd,
    StandardMessageTypes.HELLO: handshake.MsgHello,
    StandardMessageTypes.DISCONNECT: handshake.MsgDisconnect,
    StandardMessageTypes.SHUTDOWN: handshake.MsgShutdown,
    StandardMessageTypes.SHARED_PARAMETER: data.MsgSharedParameter,
}
