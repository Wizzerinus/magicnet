import dataclasses

from magicnet.netobjects.network_object import NetworkObject
from net_tester_generic import TwoNodeNetworkTester


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
