import dataclasses

from magicnet.netobjects.network_object import NetworkObject, ObjectState
from net_objects.net_tester_netobj import (
    SymmetricNetworkObjectTester,
    NetworkObjectTester,
)


def test_basics():
    @dataclasses.dataclass
    class TestNetObject(NetworkObject):
        network_name = "test_obj"
        object_role = 0

        value: int = 0

        def net_create(self) -> None:
            self.value = 1

        def net_delete(self) -> None:
            self.value = 2

    tester = SymmetricNetworkObjectTester.create_and_start(TestNetObject)
    tester.enable_debug()
    srv_object = TestNetObject(tester.server)
    assert srv_object.object_state == ObjectState.INVALID
    srv_object.request_generate()
    tester.server.transport.empty_queue()
    cl_object = tester.client.net_objects.get(srv_object.oid)
    assert cl_object is not None
    assert isinstance(cl_object, TestNetObject)
    assert cl_object.value == srv_object.value == 1
    assert cl_object.object_state == ObjectState.GENERATED
    srv_object.request_delete()
    assert cl_object.value == srv_object.value == 2
    assert cl_object.object_state == ObjectState.INVALID
    assert cl_object.oid not in tester.client.net_objects
    assert cl_object.oid not in tester.server.net_objects


def test_asymmetric():
    @dataclasses.dataclass
    class TestNetObject(NetworkObject):
        network_name = "test_obj"
        object_role = 0

        value: int = 0

        def net_create(self) -> None:
            self.value = 1

        def net_delete(self) -> None:
            self.value = 2

    @dataclasses.dataclass
    class TestNetObjectAI(NetworkObject):
        network_name = "test_obj"
        object_role = 1

        value: int = 0

        def net_create(self) -> None:
            self.value = 2

        def net_delete(self) -> None:
            self.value = 3

    tester = NetworkObjectTester.create_and_start(TestNetObjectAI, TestNetObject)
    tester.enable_debug()
    srv_object = TestNetObjectAI(tester.server)
    assert srv_object.object_state == ObjectState.INVALID
    srv_object.request_generate()
    cl_object = tester.client.net_objects.get(srv_object.oid)
    assert isinstance(cl_object, TestNetObject)
    assert cl_object.value == srv_object.value - 1 == 1
    assert cl_object.object_state == ObjectState.GENERATED
    srv_object.request_delete()
    assert cl_object.value == srv_object.value - 1 == 2
    assert cl_object.object_state == ObjectState.INVALID
    assert cl_object.oid not in tester.client.net_objects
    assert cl_object.oid not in tester.server.net_objects
