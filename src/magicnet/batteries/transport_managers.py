__all__ = ["EverywhereTransportManager"]

from collections.abc import Collection

from magicnet.core.net_message import NetMessage
from magicnet.core.transport_manager import TransportManager


class EverywhereTransportManager(TransportManager):
    """
    EverywhereTransportManager is the default transport manager.
    It will send all datagrams to all connected transport handlers.
    This may be undesired in "choke points", i.e. applications
    utilizing many different transport managers to connect to many other applications.
    In that case, a custom TransportManager should be implemented.
    """

    def resolve_destination(self, msg: NetMessage) -> Collection[str]:
        return self.transports.keys()
