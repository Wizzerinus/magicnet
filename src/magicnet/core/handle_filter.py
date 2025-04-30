__all__ = ["HandleFilter", "BaseHandleFilter"]

import abc
from collections.abc import Collection
from typing import TYPE_CHECKING, Any, Generic
from uuid import UUID

from typing_extensions import TypeVar, Unpack

from magicnet.core.net_message import NetMessage
from magicnet.util.messenger import MessengerNode

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager
    from magicnet.core.transport_handler import TransportHandler

ManagerT = TypeVar("ManagerT", bound="NetworkManager", default="NetworkManager")


class HandleFilter(MessengerNode["TransportHandler[ManagerT]", "ManagerT"], Generic[ManagerT], abc.ABC):
    """
    HandleFilter is a class that is used to filter the connection handles
    a certain message should be delivered to, on the transport level.
    Most of the time a simple one like BaseHandleFilter is sufficient,
    for more complex setups a custom one can be implemented.
    """

    @property
    def transport(self) -> "TransportHandler[ManagerT]":
        return self.parent

    @abc.abstractmethod
    def resolve_destination(self, message: NetMessage[Unpack[tuple[Any, ...]]]) -> Collection[UUID]:
        """
        Returns the set of handle IDs that a message should be delivered to.
        The message will be copied to each of the destinations here.
        All handle IDs should be valid and saved in the Transport pool.
        Transport Handler makes no guarantee on the message order
        across multiple different destinations.
        """


class BaseHandleFilter(HandleFilter[ManagerT], Generic[ManagerT]):
    """
    BaseHandleFilter is the default transport-level filter.
    By default, any message will be delivered to either `message.destination`
    or to everyone in the transport if the connection isn't set.
    """

    def resolve_destination(self, message: NetMessage[Unpack[tuple[Any, ...]]]) -> Collection[UUID]:
        return self.transport.connections.keys()
