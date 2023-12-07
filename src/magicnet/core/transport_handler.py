__all__ = ["TransportHandler", "TransportMiddleware"]

import abc
import dataclasses
import itertools
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Generic,
    TypeVar,
)
from uuid import uuid4

from magicnet.core.connection import ConnectionHandle
from magicnet.core.handle_filter import BaseHandleFilter, HandleFilter
from magicnet.core.net_globals import MNEvents, MNMathTargets
from magicnet.core.net_message import NetMessage
from magicnet.core.protocol_encoder import ProtocolEncoder
from magicnet.protocol.protocol_globals import StandardMessageTypes
from magicnet.util.messenger import MessengerNode, StandardEvents

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager

BytesOperator = Callable[[bytes], bytes]
MessageOperator = Callable[[NetMessage | None], NetMessage | None]
ManagerT = TypeVar("ManagerT", bound="NetworkManager")


@dataclasses.dataclass
class TransportMiddleware(MessengerNode, abc.ABC):
    """
    TransportMiddleware is used to modify messages sent through a transport.
    Middlewares can act on a message level (i.e., filtering unwanted messages)
    or on a bytestring level (i.e., encrypting bytestrings).
    """

    priority: int
    # Leftmost middleware will execute first on send and last on receive
    # Therefore we need to invert the order on receive

    @property
    def transport(self) -> "TransportHandler":
        return self.parent

    def add_bytes_operator(self, on_send: BytesOperator, on_recv: BytesOperator):
        self.add_math_target(MNMathTargets.BYTE_SEND, on_send, priority=self.priority)
        self.add_math_target(MNMathTargets.BYTE_RECV, on_recv, priority=-self.priority)

    def add_message_operator(self, on_send: MessageOperator, on_recv: MessageOperator):
        self.add_math_target(MNMathTargets.MSG_SEND, on_send, priority=self.priority)
        self.add_math_target(MNMathTargets.MSG_RECV, on_recv, priority=-self.priority)


@dataclasses.dataclass
class TransportHandler(MessengerNode, abc.ABC, Generic[ManagerT]):
    """
    TransportHandler represents one type of connections between the application
    and other applications on the network.
    TransportHandler is a low level mechanism that handles bytestrings
    and connection handles, while also retaining references
    to all currrently connected handles.
    """

    encoder: ProtocolEncoder
    role: str
    handle_filter: HandleFilter = dataclasses.field(default_factory=BaseHandleFilter)
    connections: dict[uuid4, ConnectionHandle] = dataclasses.field(default_factory=dict)
    middlewares: ClassVar[Collection[type[TransportMiddleware]]] = ()
    """
    Allows adding a list of middlewares to the transport protocol.
    Middlewares will be executed from left to right while sending messages,
    and in the opposite order while receiving them.
    This can be overridden on the class, as well as on the network manager
    (by passing the needed parameter into the NM constructor).
    """

    extra_middlewares: Collection[type[TransportMiddleware]] = ()

    @property
    def manager(self) -> ManagerT:
        return self.parent.parent

    def destroy_handle(self, handle: ConnectionHandle):
        self.parent.empty_queue()
        self.before_disconnect(handle)
        self.connections.pop(handle.uuid, None)

    def send_motd(self, handle: ConnectionHandle):
        self.manage_handle(handle)
        message = NetMessage(
            StandardMessageTypes.MOTD, (self.manager.motd,), f_destination=handle
        )
        self.manager.send_message(message)

    def __post_init__(self):
        self.handle_filter.parent = self
        all_middlewares = itertools.chain(self.middlewares, self.extra_middlewares)
        for index, middleware in enumerate(all_middlewares):
            self.create_child(middleware, priority=index)

    def datagram_received(self, handle: ConnectionHandle, datagram: bytes):
        datagram = self.calculate(MNMathTargets.BYTE_RECV, datagram)
        unpacked = self.encoder.unpack(datagram)
        unpacked = self.__set_connection(handle, unpacked)
        converted = self.__convert_messages(handle, unpacked, MNMathTargets.MSG_RECV)
        self.emit(MNEvents.DATAGRAM_RECEIVED, converted)

    @staticmethod
    def __set_connection(connection: ConnectionHandle, messages: Iterable[NetMessage]):
        for message in messages:
            message.sent_from = connection
            yield message

    def __convert_messages(
        self,
        handle: ConnectionHandle,
        messages: Iterable[NetMessage],
        event: MNMathTargets,
    ):
        for message in messages:
            if converted := self.calculate(event, message, handle):
                yield converted

    def deliver(self, messages: Iterable[NetMessage]) -> None:
        destinations = defaultdict(list)
        for message in messages:
            if message.f_destination is not None:
                destinations[message.f_destination.uuid].append(message)
            else:
                for handle_id in self.handle_filter.resolve_destination(message):
                    destinations[handle_id].append(message)

        for dest, message_group in destinations.items():
            if dest not in self.connections:
                self.emit(StandardEvents.WARNING, f"Unknown handle: {dest}!")
                continue
            self.__deliver_to_handle(self.connections[dest], message_group)

    def __deliver_to_handle(
        self, handle: ConnectionHandle, messages: Iterable[NetMessage]
    ) -> None:
        converted = self.__convert_messages(handle, messages, MNMathTargets.MSG_SEND)
        datagram = self.encoder.pack(converted)
        if self.manager.debug_mode:
            self.emit(StandardEvents.DEBUG, f"Sending datagram: {datagram.hex()}")
        self.send(handle, self.calculate(MNMathTargets.BYTE_SEND, datagram))

    def manage_handle(self, connection: ConnectionHandle):
        self.connections[connection.uuid] = connection

    @abc.abstractmethod
    def send(self, connection: ConnectionHandle, dg: bytes) -> None:
        """
        Sends a datagram to the other side of the network.
        The datagram will be already encoded by the NetworkManager.
        """

    @abc.abstractmethod
    def connect(self, *connection_data) -> None:
        """
        Connects to a server (remote or local, depending on transport type).
        datagram_received() should be called whenever a datagram is obtained.
        """

    @abc.abstractmethod
    def open_server(self, *args) -> None:
        """
        Beging listening on a server.
        datagram_received() should be called whenever a datagram is obtained.
        """

    @abc.abstractmethod
    def before_disconnect(self, handle: ConnectionHandle) -> None:
        """
        Runs before the handle is destroyed.
        This should do things like closing sockets, etc.
        """

    def shutdown(self):
        for handle in list(self.connections.values()):
            handle.destroy()
