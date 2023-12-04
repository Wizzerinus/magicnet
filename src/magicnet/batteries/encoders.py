__all__ = ["MsgpackEncoder"]

import json
from collections.abc import Iterator
from io import BytesIO

from magicnet.core import errors

try:
    import msgpack
except ImportError:
    msgpack = None

from magicnet.core.net_message import NetMessage
from magicnet.core.protocol_encoder import ProtocolEncoder


class MsgpackEncoder(ProtocolEncoder):
    """
    MsgpackEncoder is using Msgpack to encode messages over the wire.
    It is significantly more efficient than the builtin JSON module,
    but requires a Cython package, so may not be usable in all scenarios.
    """

    KNOWN_SYMMETRIC = True

    def __init__(self):
        if msgpack is None:
            raise errors.DependencyMissing("msgpack", "MsgpackEncoder")

    def pack(self, messages: Iterator[NetMessage]) -> bytes:
        return b"".join(msgpack.packb(msg.value) for msg in messages)

    def unpack(self, datagram: bytes) -> Iterator[NetMessage]:
        io = BytesIO()
        io.write(datagram)
        io.seek(0)
        unpacker = msgpack.Unpacker(io)
        return map(NetMessage.from_value, unpacker)


class JsonEncoder(ProtocolEncoder):
    """
    JsonEncoder is using the builtin JSON module to encode messages over the wire.
    If compatibility with an application not using MagicNet is not a concern,
    and both sides of the transport can install compiled Cython modules,
    it is recommended to use MsgpackEncoder instead.
    """

    KNOWN_SYMMETRIC = True

    def pack(self, messages: Iterator[NetMessage]) -> bytes:
        return json.dumps([msg.value for msg in messages]).encode("utf-8")

    def unpack(self, datagram: bytes) -> Iterator[NetMessage]:
        return map(NetMessage.from_value, json.loads(datagram))
