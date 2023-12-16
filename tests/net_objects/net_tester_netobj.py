import dataclasses

from magicnet.netobjects.network_object import NetworkObject
from net_tester_generic import TwoNodeNetworkTester, FlexibleNetworkTester


@dataclasses.dataclass
class NetworkObjectTester(TwoNodeNetworkTester):
    @classmethod
    def create(
        cls, server_class: type[NetworkObject], client_class: type[NetworkObject]
    ):
        tester = super().create()
        tester.server.object_registry.register_object(server_class)
        tester.server.object_registry.register_object(client_class, foreign=True)
        tester.client.object_registry.register_object(client_class)
        tester.client.object_registry.register_object(server_class, foreign=True)

        tester.server.object_registry.initialize([])
        tester.client.object_registry.initialize([])
        return tester


@dataclasses.dataclass
class SymmetricNetworkObjectTester(TwoNodeNetworkTester):
    @classmethod
    def create(cls, server_class: type[NetworkObject]):
        tester = super().create()
        tester.server.object_registry.register_object(server_class)
        tester.client.object_registry.register_object(server_class)

        tester.server.object_registry.initialize([])
        tester.client.object_registry.initialize([])
        return tester


@dataclasses.dataclass
class FlexibleNetworkObjectTester(FlexibleNetworkTester):
    client_class: type[NetworkObject] = None
    server_class: type[NetworkObject] = None

    @classmethod
    def create(
        cls, server_class: type[NetworkObject], client_class: type[NetworkObject]
    ):
        tester = super().create()
        tester.server.object_registry.register_object(server_class)
        tester.client_class = client_class
        if server_class is not client_class:
            tester.server_class = server_class
            tester.server.object_registry.register_object(client_class, foreign=True)
        tester.server.object_registry.initialize([])
        return tester

    def prepare_client(self, client):
        client.object_registry.register_object(self.client_class)
        if self.server_class:
            client.object_registry.register_object(self.server_class, foreign=True)
        client.object_registry.initialize([])
