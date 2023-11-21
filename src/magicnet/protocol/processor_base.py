import abc
from typing import TYPE_CHECKING

from magicnet.core.net_message import NetMessage
from magicnet.protocol.protocol_globals import StandardDCReasons
from magicnet.util.messenger import MessengerNode

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager


class MessageProcessor(MessengerNode, abc.ABC):
    REQUIRES_HELLO = True
    """
    Override to allow using this processor before HELLO is sent.
    """

    arg_type = None
    """
    Override to enable message validation (with the middleware).
    """

    @property
    def manager(self) -> "NetworkManager":
        return self.parent.parent

    @abc.abstractmethod
    def invoke(self, message: NetMessage):
        pass

    def __call__(self, message: NetMessage):
        if self.REQUIRES_HELLO and not message.sent_from.activated:
            message.disconnect_sender(StandardDCReasons.MESSAGE_BEFORE_HELLO)
            return
        self.invoke(message)
