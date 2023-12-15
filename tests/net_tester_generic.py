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


@dataclasses.dataclass
class NetworkTester:
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
    server: NetworkManager
    client: NetworkManager

    @classmethod
    def create(cls, *args):
        middlewares = [MessageValidatorMiddleware]
        encoder = MsgpackEncoder()
        transport = {
            "client": {
                "server": TransportParameters(encoder, SingleAppTransport, None, middlewares)
            }
        }

        def raise_err(name, msg):
            raise RuntimeError(f"{name} disconnected: {msg}")

        server = NetworkManager.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("server", transport),
            motd="An example native host",
        )
        server.listen(MNEvents.DISCONNECT, functools.partial(raise_err, "server"))
        client = NetworkManager.create_root(
            transport_type=EverywhereTransportManager,
            transport_params=("client", transport),
        )
        client.listen(MNEvents.DISCONNECT, functools.partial(raise_err, "client"))

        return cls(server, client)

    def start(self):
        self.server.open_server(client=())
        self.client.open_connection(server=[self.server])

    def enable_debug(self):
        self.server.create_child(LoggerNode, prefix="test.server")
        self.client.create_child(LoggerNode, prefix="test.client")
