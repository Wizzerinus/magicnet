__all__ = ["MessageValidatorMiddleware"]

import dataclasses
from collections.abc import Callable
from typing import Any, cast

from magicnet.core.connection import ConnectionHandle
from magicnet.core.errors import DataValidationError
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.core.transport_handler import TransportMiddleware
from magicnet.protocol.network_typechecker import check_type
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.util.messenger import StandardEvents


def create_validator(input_type: type) -> Callable[[Any], tuple[bool, Any]]:
    def test(value):
        try:
            check_type(value, input_type)
        except DataValidationError as e:
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
        self.validators = {}
        self.listen(MNEvents.BEFORE_LAUNCH, self.do_before_launch)

    def do_before_launch(self):
        all_methods = self.transport.manager.dg_processor.children.items()
        for ident, method in all_methods:
            method = cast(MessageProcessor, method)
            if method.arg_type is not None:
                validator = create_validator(method.arg_type)
                self.validators[ident] = validator
        self.add_message_operator(self.validate_message_send, self.validate_message)

    def validate_message(
        self, message: NetMessage, _handle: ConnectionHandle, *, do_warn: bool = True
    ):
        if message.message_type not in self.validators:
            return message
        valid, params = self.validators[message.message_type](message.parameters)
        if not valid:
            if do_warn:
                self.emit(
                    StandardEvents.WARNING,
                    f"Invalid parameters received: {params}! Ignoring.",
                )
            return None
        message.parameters = params
        return message

    def validate_message_send(self, message: NetMessage, handle: ConnectionHandle):
        if not self.validate_message(message, handle, do_warn=False):
            raise TypeError(f"Invalid parameters in message: {message}")
        return message
