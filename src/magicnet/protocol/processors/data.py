__all__ = []

from magicnet.core.net_message import NetMessage
from magicnet.protocol import network_types
from magicnet.protocol.processor_base import MessageProcessor


class MsgSharedParameter(MessageProcessor):
    REQUIRES_HELLO = False
    arg_type = tuple[network_types.s16, network_types.hashable]

    def invoke(self, message: NetMessage):
        param_name, param_value = message.parameters
        message.sent_from.shared_parameters[param_name] = param_value
