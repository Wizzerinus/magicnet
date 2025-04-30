__all__ = ["EverywhereTransportManager"]

from collections.abc import Collection
from typing import Any

from typing_extensions import Unpack

from magicnet.core.net_message import NetMessage
from magicnet.core.transport_handler import ManagerT
from magicnet.core.transport_manager import TransportManager


class EverywhereTransportManager(TransportManager[ManagerT]):
    """
    EverywhereTransportManager is the default transport manager.
    It will send all datagrams to all connected transport handlers.
    This may be undesired in "choke points", i.e. applications
    utilizing many different transport managers to connect to many other applications.
    In that case, a custom TransportManager should be implemented.
    """

    def resolve_destination(self, msg: NetMessage[Unpack[tuple[Any, ...]]]) -> Collection[str]:
        return self.transports.keys()
