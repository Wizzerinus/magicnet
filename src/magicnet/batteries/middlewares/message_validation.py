__all__ = ["MessageValidatorMiddleware"]

import dataclasses
from collections.abc import Callable
from typing import Any, cast

try:
    # TODO: reimplement this middleware in a less stupid way
    #  because it has issues when bytestrings are involved
    from pydantic import BaseModel, ValidationError
except ImportError:
    ValidationError = BaseModel = None

from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.core.transport_handler import TransportMiddleware
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.util.messenger import StandardEvents


def create_validator(input_type: type) -> Callable[[Any], bool]:
    class C(BaseModel):
        args: input_type

    def test(value):
        try:
            C(args=value)
        except ValidationError:
            return False
        else:
            return True

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
        if BaseModel is None:
            raise RuntimeError("Pydantic is required to use MessageValidator!")

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

    def validate_message(self, message: NetMessage, *, do_warn: bool = True):
        if message.message_type not in self.validators:
            return message
        if not self.validators[message.message_type](message.parameters):
            if do_warn:
                self.emit(
                    StandardEvents.WARNING,
                    f"Invalid parameters received: {message}! Ignoring.",
                )
            return None
        return message

    def validate_message_send(self, message: NetMessage):
        if not self.validate_message(message, do_warn=False):
            raise TypeError(f"Invalid parameters in message: {message}")
        return message
