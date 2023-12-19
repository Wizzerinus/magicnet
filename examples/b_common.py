from typing import Collection
from uuid import uuid4

from magicnet.batteries.encoders import MsgpackEncoder
from magicnet.batteries.middlewares.message_validation import MessageValidatorMiddleware
from magicnet.batteries.transports.socket_asyncio import AsyncIOSocketTransport
from magicnet.core.handle_filter import BaseHandleFilter
from magicnet.core.net_message import NetMessage
from magicnet.core.transport_manager import TransportParameters
from magicnet.protocol import network_types
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.util.messenger import StandardEvents


class MsgSetName(MessageProcessor):
    arg_type = tuple[network_types.s16]

    def invoke(self, message: NetMessage):
        message.sent_from.context["username"] = message.parameters[0]
        print(
            f"Client {message.sent_from.uuid} set their username:",
            message.parameters[0],
        )


class MsgCustom(MessageProcessor):
    arg_type = tuple[network_types.s256]

    def invoke(self, message: NetMessage):
        client_name = message.sent_from.context.get("username")
        if not client_name:
            message.disconnect_sender(10, "MsgCustom requires a username!")
            return

        print(f"Client {client_name} sent:", message.parameters[0])
        to_send = NetMessage(
            MSG_CUSTOM_RESP,
            ("".join(reversed(message.parameters[0])),),
            destination=message.sent_from,
        )
        self.manager.send_message(to_send)
        # The filter used here will use `routing_data` to broadcast
        # to everyone except the destination, see below
        broadcast = NetMessage(
            MSG_BROADCAST,
            (client_name, message.parameters[0]),
            routing_data=message.sent_from,
        )
        self.manager.send_message(broadcast)


class MsgCustomResponse(MessageProcessor):
    arg_type = tuple[network_types.s256]

    def invoke(self, message: NetMessage):
        print("Reversed message:", message.parameters[0])


class MsgBroadcast(MessageProcessor):
    arg_type = tuple[network_types.s16, network_types.s256]

    def invoke(self, message: NetMessage):
        name, text = message.parameters
        self.emit(StandardEvents.INFO, f"{name} said: {text}")


MSG_SET_NAME = 64
MSG_CUSTOM = 65
MSG_CUSTOM_RESP = 66
MSG_BROADCAST = 67

extra_message_types = {
    MSG_SET_NAME: MsgSetName,
    MSG_CUSTOM: MsgCustom,
    MSG_CUSTOM_RESP: MsgCustomResponse,
    MSG_BROADCAST: MsgBroadcast,
}


class EverywhereExceptBack(BaseHandleFilter):
    def resolve_destination(self, message: NetMessage) -> Collection[uuid4]:
        if message.message_type == MSG_BROADCAST:
            return [
                k
                for k in self.transport.connections.keys()
                if k != message.routing_data.uuid
            ]
        return super().resolve_destination(message)


middlewares = [MessageValidatorMiddleware]
encoder = MsgpackEncoder()
transport = {
    "client": {
        "server": TransportParameters(
            encoder, AsyncIOSocketTransport, EverywhereExceptBack, middlewares
        )
    }
}
