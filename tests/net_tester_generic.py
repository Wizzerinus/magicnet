import abc
import dataclasses
import functools
from typing import TypeVar

from magicnet.batteries.encoders import MsgpackEncoder
from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.middlewares.message_validation import MessageValidatorMiddleware
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.batteries.transports.single_app import SingleAppTransport
from magicnet.core.net_globals import MNEvents
from magicnet.core.network_manager import NetworkManager
from magicnet.core.transport_manager import TransportParameters

T = TypeVar("T", bound="NetworkTester")


class NetworkTester(abc.ABC):
    middlewares = [MessageValidatorMiddleware]
    server_middlewares = [MessageValidatorMiddleware]
    encoder = MsgpackEncoder()

    @classmethod
    def transport(cls):
        return {
            "client": {
                "server": TransportParameters(
                    cls.encoder, SingleAppTransport, None, cls.middlewares
                )
            }
        }

    @classmethod
    def server_transport(cls):
        return {
            "client": {
                "server": TransportParameters(
                    cls.encoder, SingleAppTransport, None, cls.server_middlewares
                )
            }
        }

    @abc.abstractmethod
    def start(self):
        pass

    @classmethod
    @abc.abstractmethod
    def create(cls, *args):
        pass

    @abc.abstractmethod
    def enable_debug(self):
        pass

    @classmethod
    def create_and_start(cls: type[T], *args) -> T:
        tester = cls.create(*args)
        tester.start()
        return tester


@dataclasses.dataclass
class TwoNodeNetworkTester(NetworkTester):
    server_cls = NetworkManager
    client_cls = NetworkManager
    do_raise_err = True

    server: NetworkManager
    client: NetworkManager

    @classmethod
    def create(cls, *args):
        def raise_err(name, msg):
            raise RuntimeError(f"{name} disconnected: {msg}")

        server = cls.server_cls.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("server", cls.server_transport()),
            motd="An example native host",
            client_repository=64,
        )
        client = cls.client_cls.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("client", cls.transport()),
        )
        if cls.do_raise_err:
            server.listen(MNEvents.DISCONNECT, functools.partial(raise_err, "server"))
            client.listen(MNEvents.DISCONNECT, functools.partial(raise_err, "client"))

        return cls(server, client)

    def start(self):
        self.server.open_server(client=())
        self.client.open_connection(server=[self.server])

    def enable_debug(self):
        self.server.create_child(LoggerNode, prefix="test.server")
        self.client.create_child(LoggerNode, prefix="test.client")


@dataclasses.dataclass
class FlexibleNetworkTester(NetworkTester, abc.ABC):
    server: NetworkManager
    clients: list[NetworkManager] = dataclasses.field(default_factory=list)
    debug: bool = False

    @classmethod
    def create(cls, *args):
        def raise_err(name, msg):
            raise RuntimeError(f"{name} disconnected: {msg}")

        server = NetworkManager.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("server", cls.server_transport()),
            motd="An example native host",
            client_repository=64,
        )
        server.listen(MNEvents.DISCONNECT, functools.partial(raise_err, "server"))
        return cls(server=server)

    def start(self):
        self.server.open_server(client=())

    @abc.abstractmethod
    def prepare_client(self, client: NetworkManager):
        pass

    def make_client(self) -> NetworkManager:
        def raise_err(name, msg):
            raise RuntimeError(f"{name} disconnected: {msg}")

        client = NetworkManager.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("client", self.transport()),
        )
        client.listen(MNEvents.DISCONNECT, functools.partial(raise_err, "client"))
        if self.debug:
            client.create_child(LoggerNode, prefix=f"test.client-{len(self.clients)}")
        self.clients.append(client)
        self.prepare_client(client)
        client.open_connection(server=[self.server])
        return client

    def enable_debug(self):
        self.server.create_child(LoggerNode, prefix="test.server")
        self.debug = True
        for idx, client in enumerate(self.clients):
            client.create_child(LoggerNode, prefix=f"test.client-{idx}")
