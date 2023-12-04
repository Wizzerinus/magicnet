__all__ = ["TransportManager", "TransportParameters"]

import abc
import contextlib
import dataclasses
from collections import defaultdict
from collections.abc import Collection, Iterable
from typing import TypeVar, cast

from magicnet.core import errors
from magicnet.core.handle_filter import HandleFilter
from magicnet.core.net_message import NetMessage
from magicnet.core.protocol_encoder import ProtocolEncoder
from magicnet.core.transport_handler import TransportHandler, TransportMiddleware
from magicnet.util.messenger import MessengerNode, StandardEvents


@dataclasses.dataclass
class TransportParameters:
    encoder: ProtocolEncoder
    transport: type[TransportHandler]
    filter: type[HandleFilter] | None = None
    middlewares: Collection[type[TransportMiddleware]] = ()


TransportActiveType = dict[str, TransportHandler]
TransportRowType = dict[str, TransportParameters]
TransportMatrixType = dict[str, TransportRowType]
TransportAnyType = TransportRowType | TransportMatrixType
T = TypeVar("T", bound="TransportManager")


def extract_transport_method(
    parent: "TransportManager", role: str, matrix: TransportAnyType
) -> TransportActiveType:
    if role not in matrix:
        use_matrix = True
    else:
        use_matrix = isinstance(matrix[role], dict)

    if use_matrix:
        matrix = cast(TransportMatrixType, matrix)
        row = dict(matrix.get(role, {}))
        # Some magic to allow defining tables by only defining one of the two cells
        # i.e. defining {"Client": {"MessageDirector": ...}}
        # but not defininig {"MessageDirector": {"Client": ...}}
        # Requires that the encoder is defined as symmetric or has a symmetrize() func
        for that_role in matrix:
            if role == that_role or that_role in row or role not in matrix[that_role]:
                continue
            params: TransportParameters = matrix[that_role][role]
            row[that_role] = TransportParameters(
                params.encoder.symmetrize(),
                params.transport,
                params.filter,
                params.middlewares,
            )
    else:
        row = cast(TransportRowType, matrix)

    output = {}
    for that_role, params in row.items():
        kwargs = dict(
            role=that_role, encoder=params.encoder, extra_middlewares=params.middlewares
        )
        if params.filter is not None:
            kwargs["handle_filter"] = params.filter()
        transport = parent.create_child(params.transport, **kwargs)
        output[that_role] = transport

    return output


@dataclasses.dataclass
class TransportManager(MessengerNode, abc.ABC):
    """
    TransportManager is a mid-level mechanism used to integrate
    one or more TransportHandlers together. It is also used
    to gather messages together to potentially reduce network load
    (and also increases stability of the SingleAppTransport).
    """

    role: str
    transports: dict[str, TransportHandler]
    queue_active: bool = False
    __delivery_queue: list[NetMessage] = dataclasses.field(default_factory=list)

    @classmethod
    def from_map(
        cls: T,
        parent: MessengerNode,
        role: str,
        transport_map: TransportAnyType,
    ) -> T:
        obj = cls(role=role, transports={}, _parent=parent)
        obj.transports = extract_transport_method(obj, role, transport_map)
        return obj

    def __post_init__(self):
        for transport in self.transports.values():
            transport.parent = self

    @abc.abstractmethod
    def resolve_destination(self, msg: NetMessage) -> Collection[str]:
        """
        Returns the set of roles that a message should be delivered to.
        The message will be copied to each of the destinations here.
        Transport Manager makes no guarantee on the message order
        across multiple different destinations.
        """

    def send(self, message: NetMessage):
        if self.queue_active:
            self.__delivery_queue.append(message)
        else:
            self.__deliver([message])

    @property
    @contextlib.contextmanager
    def message_queue(self):
        if self.queue_active:
            # Do not need to do anything here
            yield
            return

        self.queue_active = True
        yield
        self.queue_active = False
        self.empty_queue()

    def empty_queue(self):
        if self.__delivery_queue:
            queue = self.__delivery_queue
            self.__delivery_queue = []
            self.__deliver(queue)

    def __deliver(self, messages: Iterable[NetMessage]) -> None:
        destinations = defaultdict(list)
        for message in messages:
            for dest in self.resolve_destination(message):
                destinations[dest].append(message)

        for dest, message_group in destinations.items():
            if dest not in self.transports:
                self.emit(StandardEvents.ERROR, f"Unknown network role: {dest}!")
            self.transports[dest].deliver(message_group)

    def open_servers(self, **kwargs):
        for role in kwargs:
            if role not in self.transports:
                raise errors.UnknownRole(role)

        for role, args in kwargs.items():
            transport = self.transports[role]
            transport.open_server(*args)

    def make_connections(self, **kwargs):
        for role in kwargs:
            if role not in self.transports:
                raise errors.UnknownRole(role)

        for role, args in kwargs.items():
            transport = self.transports[role]
            transport.connect(*args)

    def shutdown_connections(self):
        for transport in self.transports.values():
            transport.shutdown()
