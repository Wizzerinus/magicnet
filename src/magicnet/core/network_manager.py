__all__ = ["NetworkManager"]

import dataclasses
from collections.abc import Iterable
from typing import Generic, TypeVar

from magicnet.core import errors
from magicnet.core.datagram_processor import DatagramProcessor
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage, standard_range
from magicnet.core.network_object import NetworkObject
from magicnet.core.transport_manager import TransportManager
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.protocol.protocol_globals import StandardMessageTypes
from magicnet.util.messenger import MessengerNode, StandardEvents

AnyNetObject = TypeVar("AnyNetObject", bound=NetworkObject)


@dataclasses.dataclass
class NetworkManager(MessengerNode, Generic[AnyNetObject]):
    """
    NetworkManager is the base class for MagicNetworking's operation.
    One has to be created to use this library. An example use::

        middlewares = [MessageValidatorMiddleware]
        encoder = MsgpackEncoder()
        params = TransportParameters(encoder, AsyncIOSocketTransport, None, middlewares)
        transport = {"client": {"server": params}}
        server = AsyncIONetworkManager.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("server", transport),
            motd="An example server host",
        )
    """

    transport: TransportManager = None
    """Usually this is autogenerated from transport_type and transport_params"""
    dg_processor: DatagramProcessor = None
    """Internal object, used to process NetMessages"""
    managed_objects: dict[int, AnyNetObject] = dataclasses.field(default_factory=dict)
    """Managed Network objects, see documentation for those."""
    extras: dict[int, type[MessageProcessor]] = None
    """Additional types of messages that should be processed."""
    network_hash: bytes = bytes.fromhex("12345678")
    """This can be used as an additional form of client validation."""
    motd: str = None
    """This will be sent to the clients before CLIENT_HELLO is received."""
    transport_type: type[TransportManager] = None
    transport_params: tuple = None
    shutdown_on_disconnect: bool = False
    """If true, the manager will be closed when any handle disconnects"""

    @property
    def role(self) -> str:
        return self.transport.role

    def __post_init__(self):
        if self.extras and any(value in standard_range for value in self.extras):
            raise errors.ExtraCallbacksProvided()
        if self.transport is not None:
            self.transport.parent = self
        elif self.transport_type is not None and self.transport_params is not None:
            self.transport = self.transport_type.from_map(self, *self.transport_params)
            self.transport.parent = self
        else:
            raise errors.ComponentNotProvided("transport")
        self.dg_processor = self.create_child(DatagramProcessor, extras=self.extras)
        self.listen(MNEvents.DATAGRAM_RECEIVED, self.process_datagram)
        if self.shutdown_on_disconnect:
            self.listen(MNEvents.HANDLE_DESTROYED, self.shutdown_with_handle)

    def shutdown_with_handle(self, _h):
        # I tried to make this into a lambda, but it did not work
        # for some absolutely unknown reasons.
        self.shutdown()

    def send_message(self, message: NetMessage):
        self.transport.send(message)

    def process_datagram(self, messages: Iterable[NetMessage]):
        with self.transport.message_queue:
            for msg in messages:
                self.dg_processor.process_message(msg)

    def open_server(self, **kwargs):
        """
        Starts one or more servers.
        Note that kwargs should map the foreign role to the parameters
        provided to that role. So if you run this on a node with
        the role = 'server', and the other node in your network
        is called 'client', you should map 'client' to the parameters.

        This function should be non-blocking, but other types of NetworkManagers
        may make it blocking (see: AsyncIONetworkManager).
        """

        if not kwargs:
            raise errors.ConnectionParametersMissing("open_server")
        self.emit(MNEvents.BEFORE_LAUNCH)
        self.emit(StandardEvents.INFO, "Opening network servers!")
        self.transport.open_servers(**kwargs)

    def open_connection(self, **kwargs):
        """
        Connects to one or more servers.
        Note that kwargs should map the foreign role to the parameters
        provided to that role. So if you run this on a node with
        the role = 'client', and the other node in your network
        is called 'server', you should map 'server' to the parameters.

        This function should be non-blocking, but other types of NetworkManagers
        may make it blocking (see: AsyncIONetworkManager).
        """

        if not kwargs:
            raise errors.ConnectionParametersMissing("open_connection")

        self.emit(MNEvents.BEFORE_LAUNCH)
        self.emit(StandardEvents.INFO, "Connecting to a server!")
        self.transport.make_connections(**kwargs)

    def shutdown(self):
        self.emit(StandardEvents.INFO, "Shutting down!")
        self.emit(MNEvents.BEFORE_SHUTDOWN)
        msg = NetMessage(StandardMessageTypes.SHUTDOWN)
        self.send_message(msg)
        self.transport.shutdown_connections()
