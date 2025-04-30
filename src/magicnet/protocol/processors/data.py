__all__ = []

from typing import Any, final

from magicnet.core.net_message import NetMessage
from magicnet.protocol import network_types
from magicnet.protocol.processor_base import MessageProcessor


@final
class MsgSharedParameter(MessageProcessor[str, Any]):
    REQUIRES_HELLO = False
    arg_type = tuple[network_types.s16, network_types.hashable]

    def invoke(self, message: NetMessage[str, Any]):
        assert message.sent_from
        param_name, param_value = message.parameters
        message.sent_from.shared_parameters[param_name] = param_value
