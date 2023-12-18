__all__ = ["NetworkManager"]

import dataclasses
import pathlib
from collections.abc import Iterable
from typing import Generic, TypeVar

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.datagram_processor import DatagramProcessor
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage, client_repo_range, standard_range
from magicnet.core.transport_manager import TransportManager
from magicnet.netobjects.network_object import NetworkObject
from magicnet.netobjects.network_object_manager import NetworkObjectManager
from magicnet.netobjects.network_object_registry import NetworkObjectRegistry
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
    object_manager: NetworkObjectManager = None
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
    repository_allocator: int = dataclasses.field(
        init=False, default=max(client_repo_range)
    )
    """We start the repository allocation from 128 and declare 1-127 hardcoded"""
    client_repository: int | None = None
    """
    Client repository index, must be a number from 1-127 or None.
    Only clients that have this repository may distribute locally created objects.
    Note that MagicNet itself does not enforce that, so you want a middleware
    to control that.
    """
    object_signature_filenames: list[str | pathlib.Path] = None
    """
    Filenames of the json files with the object signatures.
    If omitted no signatures will be automatically loaded.
    """
    marshalling_mode: str | pathlib.Path | None = None
    """
    If this is set to a string, the manager will dump the marshalled
    configuration of its network objects into the file with this name.
    """

    debug_mode: bool = False

    current_message: NetMessage | None = dataclasses.field(default=None, init=False)

    @property
    def current_sender(self) -> ConnectionHandle | None:
        return self.current_message.sent_from if self.current_message else None

    @property
    def managed_objects(self) -> dict[int, AnyNetObject]:
        return self.object_manager.managed_objects

    def make_repository(self) -> int:
        self.repository_allocator += 1
        return self.repository_allocator

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

        if self.client_repository is not None:
            if self.client_repository not in client_repo_range:
                raise errors.InvalidClientRepository(self.client_repository)

        self.object_manager = NetworkObjectManager(_parent=self)
        self.object_registry = NetworkObjectRegistry(_parent=self)
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
                if self.debug_mode:
                    self.emit(StandardEvents.DEBUG, f"Received message: {msg}")

                self.current_message = msg
                try:
                    self.dg_processor.process_message(msg)
                except Exception as e:  # noqa: BLE001
                    self.emit(
                        StandardEvents.EXCEPTION, "Error while processing a message", e
                    )
                self.current_message = None

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

    def get_handle(self, remote_role: str) -> ConnectionHandle | None:
        """
        Returns a handle identifying connection with a certain client role.
        If there are multiple connections to clients with that role,
        can return any of them, and is intended to be only used
        in scenarios where there is supposed to be only one such handle.
        """

        return self.transport.get_handle(remote_role)
