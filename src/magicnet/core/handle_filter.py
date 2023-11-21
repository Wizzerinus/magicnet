__all__ = ["HandleFilter", "BaseHandleFilter"]

import abc
from collections.abc import Collection
from typing import TYPE_CHECKING
from uuid import uuid4

from magicnet.core.net_message import NetMessage
from magicnet.util.messenger import MessengerNode

if TYPE_CHECKING:
    from magicnet.core.transport_handler import TransportHandler


class HandleFilter(MessengerNode, abc.ABC):
    """
    HandleFilter is a class that is used to filter the connection handles
    a certain message should be delivered to, on the transport level.
    Most of the time a simple one like BaseHandleFilter is sufficient,
    for more complex setups a custom one can be implemented.
    """

    @property
    def transport(self) -> "TransportHandler":
        return self.parent

    @abc.abstractmethod
    def resolve_destination(self, message: NetMessage) -> Collection[uuid4]:
        """
        Returns the set of handle IDs that a message should be delivered to.
        The message will be copied to each of the destinations here.
        All handle IDs should be valid and saved in the Transport pool.
        Transport Handler makes no guarantee on the message order
        across multiple different destinations.
        """


class BaseHandleFilter(HandleFilter):
    """
    BaseHandleFilter is the default transport-level filter.
    By default, any message will be delivered to either `message.destination`
    or to everyone in the transport if the connection isn't set.
    """

    def resolve_destination(self, message: NetMessage) -> Collection[uuid4]:
        if message.destination is not None:
            return [message.destination.uuid]
        return self.transport.connections.keys()
