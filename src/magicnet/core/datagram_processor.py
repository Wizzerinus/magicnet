__all__ = ["DatagramProcessor"]

import dataclasses
import itertools
from typing import TYPE_CHECKING, Any

from typing_extensions import Unpack

from magicnet.core.net_message import NetMessage, standard_range
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.util.messenger import MessengerNode, StandardEvents

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager


@dataclasses.dataclass
class DatagramProcessor(MessengerNode["NetworkManager", "NetworkManager"]):
    """
    DatagramProcessor is a helper class that is added as a child to the NetworkManager.
    Usually the use of this class should not be needed.
    """

    extras: dict[int, type[MessageProcessor[Unpack[tuple[Any, ...]]]]] = dataclasses.field(default_factory=dict)
    processors: dict[int, MessageProcessor[Unpack[tuple[Any, ...]]]] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        # Prevent an import loop
        from magicnet.protocol.message_processors import message_processors

        for msg_id, constructor in itertools.chain(
            message_processors.items(), (self.extras.items() if self.extras else [])
        ):
            self.processors[msg_id] = self.create_child(constructor)

    def process_message(self, message: NetMessage[Unpack[tuple[Any, ...]]]):
        if message.message_type in self.processors:
            self.processors[message.message_type](message)
        elif message.message_type in standard_range:
            self.emit(
                StandardEvents.ERROR,
                f"Unknown standard message code: {message.message_type}!",
            )
        else:
            self.emit(StandardEvents.WARNING, f"Unknown message code: {message.message_type}!")
