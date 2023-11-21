__all__ = ["DatagramProcessor"]

import dataclasses
import itertools

from magicnet.core.net_message import NetMessage, standard_range
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.util.messenger import MessengerNode, StandardEvents


@dataclasses.dataclass
class DatagramProcessor(MessengerNode):
    """
    DatagramProcessor is a helper class that is added as a child to the NetworkManager.
    Usually the use of this class should not be needed.
    """

    extras: dict[int, type[MessageProcessor]] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        # Prevent an import loop
        from magicnet.protocol.message_processors import message_processors

        for msg_id, constructor in itertools.chain(
            message_processors.items(), (self.extras.items() if self.extras else [])
        ):
            self.create_child(constructor, msg_id)

    def process_message(self, message: NetMessage):
        if message.message_type in self.children:
            self.children[message.message_type](message)
        elif message.message_type in standard_range:
            self.emit(
                StandardEvents.ERROR,
                f"Unknown standard message code: {message.message_type}!",
            )
        else:
            self.emit(
                StandardEvents.WARNING, f"Unknown message code: {message.message_type}!"
            )
