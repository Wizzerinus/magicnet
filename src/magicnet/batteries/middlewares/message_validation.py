__all__ = ["MessageValidatorMiddleware"]

import dataclasses
from collections.abc import Callable
from typing import Any

from typing_extensions import Unpack

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.core.transport_handler import TransportMiddleware
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.util.messenger import StandardEvents
from magicnet.util.typechecking.magicnet_typechecker import check_type


def create_validator(input_type: type) -> Callable[[Any], tuple[bool, Any]]:
    def test(value: Any):
        try:
            check_type(value, input_type)
        except errors.DataValidationError as e:
            return False, str(e)
        else:
            return True, value

    return test


@dataclasses.dataclass
class MessageValidatorMiddleware(TransportMiddleware):
    """
    Enables automatic message validation on all incoming and outgoing messages.
    Incoming messages will be ignored and a warning raised;
    Outgoing messages will cause a TypeError (which may or may not cause a crash
    depending on the configuration of the NetworkManager).
    """

    def __post_init__(self):
        self.validators: dict[int, type[tuple[Any, ...]]] = {}
        self.listen(MNEvents.BEFORE_LAUNCH, self.do_before_launch)

    def do_before_launch(self):
        all_methods = self.transport.manager.dg_processor.children.items()
        for ident, method in all_methods:
            assert isinstance(method, MessageProcessor)
            if method.arg_type is not None:
                self.validators[int(ident)] = method.arg_type
        self.add_message_operator(self.validate_message_send, self.validate_message_recv)

    def validate_message_send(self, message: NetMessage[Unpack[tuple[Any, ...]]], _handle: ConnectionHandle):
        if message.message_type not in self.validators:
            return message

        # will raise if something is wrong
        check_type(message.parameters, self.validators[message.message_type])
        return message

    def validate_message_recv(self, message: NetMessage[Unpack[tuple[Any, ...]]], _handle: ConnectionHandle):
        if message.message_type not in self.validators:
            return message

        try:
            check_type(message.parameters, self.validators[message.message_type])
        except errors.DataValidationError as e:
            self.emit(StandardEvents.WARNING, f"Invalid parameters in message {message}: {e}")
        else:
            return message
