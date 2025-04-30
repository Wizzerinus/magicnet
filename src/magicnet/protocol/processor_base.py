import abc
from typing import TYPE_CHECKING, Any, ClassVar, Generic

from typing_extensions import TypeVarTuple, Unpack

from magicnet.core.net_message import NetMessage
from magicnet.protocol.protocol_globals import StandardDCReasons
from magicnet.util.messenger import MessengerNode

if TYPE_CHECKING:
    from magicnet.core.datagram_processor import DatagramProcessor
    from magicnet.core.network_manager import NetworkManager


Ts = TypeVarTuple("Ts")


class MessageProcessor(MessengerNode["DatagramProcessor", "NetworkManager"], Generic[Unpack[Ts]], abc.ABC):
    REQUIRES_HELLO: ClassVar[bool] = True
    """
    Override to allow using this processor before HELLO is sent.
    """

    arg_type: type[tuple[Any, ...]] | None = None
    """
    Override to enable message validation (with the middleware).
    """

    @property
    def manager(self) -> "NetworkManager":
        return self.parent.parent

    @abc.abstractmethod
    def invoke(self, message: NetMessage[Unpack[tuple[Any, ...]]]):
        pass

    def __call__(self, message: NetMessage[Unpack[tuple[Any, ...]]]):
        assert message.sent_from
        if self.REQUIRES_HELLO and not message.sent_from.activated:
            message.disconnect_sender(StandardDCReasons.MESSAGE_BEFORE_HELLO)
            return
        self.invoke(message)
