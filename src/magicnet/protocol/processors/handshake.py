__all__ = []

from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.protocol import network_types
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.protocol.protocol_globals import (
    StandardDCReasons,
    StandardMessageTypes,
    mn_proto_version,
)
from magicnet.util.messenger import StandardEvents


class MsgMotd(MessageProcessor):
    REQUIRES_HELLO = False
    arg_type = tuple[network_types.s64]

    def invoke(self, message: NetMessage):
        if message.sent_from.activated:
            self.emit(StandardEvents.WARNING, "MOTD sent multiple times!")
            return
        motd = message.parameters[0]
        self.emit(MNEvents.MOTD_SET, motd)
        second_message = NetMessage(
            StandardMessageTypes.HELLO,
            (mn_proto_version, self.manager.network_hash),
            f_destination=message.sent_from,
        )
        self.manager.send_message(second_message)
        message.sent_from.activate()


class MsgHello(MessageProcessor):
    REQUIRES_HELLO = False
    arg_type = tuple[network_types.uint16, network_types.bs64]

    def invoke(self, message: NetMessage):
        if message.sent_from.activated:
            message.disconnect_sender(StandardDCReasons.HELLO_MULTIPLE)
            return
        proto_major, nm_hash = message.parameters
        if proto_major != mn_proto_version:
            message.disconnect_sender(StandardDCReasons.HELLO_INVALID_PROTO_VER)
            return
        if nm_hash != self.manager.network_hash:
            message.disconnect_sender(StandardDCReasons.HELLO_HASH_MISMATCH)
            return
        message.sent_from.activate()
        message.sent_from.set_shared_parameter("rp", self.manager.make_repository())


class MsgDisconnect(MessageProcessor):
    REQUIRES_HELLO = False
    arg_type = tuple[network_types.uint8, network_types.s64 | None]

    DISCONNECT_REASONS = {
        StandardDCReasons.HELLO_MULTIPLE: "HELLO message sent multiple times!",
        StandardDCReasons.HELLO_HASH_MISMATCH: "The server hash does not match!",
        StandardDCReasons.HELLO_INVALID_PROTO_VER: "The server version does not match!",
        StandardDCReasons.MESSAGE_BEFORE_HELLO: "A different message sent before HELLO!",
    }

    def get_reason_description(self, reason: StandardDCReasons) -> str:
        return self.DISCONNECT_REASONS.get(reason, "Unknown disconnection reason")

    def invoke(self, message: NetMessage):
        reason, reason_name = message.parameters
        reason_desc = self.get_reason_description(reason)
        if reason_name:
            reason_desc = f"{reason_desc}: {reason_name}"
        self.emit(MNEvents.DISCONNECT, reason_desc)
        message.sent_from.destroy()


class MsgShutdown(MessageProcessor):
    REQUIRES_HELLO = False
    arg_type = tuple[()]

    def invoke(self, message: NetMessage):
        message.sent_from.destroy()
