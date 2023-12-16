import dataclasses
from unittest.mock import MagicMock

from magicnet.core.net_globals import MNEvents
from magicnet.netobjects.network_field import NetworkField
from magicnet.netobjects.network_object import NetworkObject
from magicnet.protocol import network_types
from net_objects.net_tester_netobj import (
    SymmetricNetworkObjectTester,
    FlexibleNetworkObjectTester,
)


def test_network_calls():
    @dataclasses.dataclass
    class TestNetObject(NetworkObject):
        network_name = "test_obj"
        object_role = 0

        value: int = 0

        @NetworkField
        def set_value(self, value: network_types.uint16 = 256):
            self.value = value

        def net_create(self) -> None:
            pass

        def net_delete(self) -> None:
            pass

    tester = SymmetricNetworkObjectTester.create_and_start(TestNetObject)
    srv_object = TestNetObject(tester.server)
    srv_object.request_generate()

    cl_object = tester.client.managed_objects.get(srv_object.oid)
    assert cl_object.value == srv_object.value == 0

    srv_object.send_message("set_value")
    assert cl_object.value == 256
    assert srv_object.value == 0

    srv_object.send_message("set_value", [100])
    assert cl_object.value == 100
    assert srv_object.value == 0

    object_mock = MagicMock()
    cl_object.listen(MNEvents.BAD_NETWORK_OBJECT_CALL, object_mock)
    srv_object.send_message("set_value", [100000])
    assert cl_object.value == 100
    assert object_mock.call_args.args[0]["reason"] == "bad-args"
    assert "Lt(65536)" in object_mock.call_args.args[0]["msg"]

    srv_object.send_message("set_value", [1, 2, 3])
    assert cl_object.value == 100
    assert object_mock.call_args.args[0]["reason"] == "bad-args"
    assert "many arguments" in object_mock.call_args.args[0]["msg"]


def test_dataclasses_arguments():
    @dataclasses.dataclass
    class MyStruct:
        a: int = 0
        b: int = 0
        c: int = 0

    @dataclasses.dataclass
    class TestNetObject(NetworkObject):
        network_name = "test_obj"
        object_role = 0

        value: MyStruct = None
        extras: tuple[str, ...] = ()

        @NetworkField
        def set_value(self, item: MyStruct, *extras: str):
            self.value = item
            self.extras = extras

        def net_create(self) -> None:
            pass

        def net_delete(self) -> None:
            pass

    tester = SymmetricNetworkObjectTester.create_and_start(TestNetObject)
    srv_object = TestNetObject(tester.server)
    srv_object.request_generate()

    cl_object = tester.client.managed_objects.get(srv_object.oid)
    assert cl_object.value is None and srv_object.value is None

    srv_object.send_message("set_value", [(1, 2, 3)])
    assert cl_object.value == MyStruct(1, 2, 3)
    srv_object.send_message("set_value", [MyStruct(4, 5, 6)])
    assert cl_object.value == MyStruct(4, 5, 6)
    srv_object.send_message("set_value", [MyStruct(4, 5, 6), "a", "b"])
    assert cl_object.extras == ("a", "b")

    object_mock = MagicMock()
    cl_object.listen(MNEvents.BAD_NETWORK_OBJECT_CALL, object_mock)
    srv_object.send_message("set_value", [MyStruct(4, 5, 6), 1])
    assert cl_object.extras == ("a", "b")
    assert object_mock.call_args.args[0]["reason"] == "bad-args"
    assert "expected str" in object_mock.call_args.args[0]["msg"]


def test_field_visibility():
    @dataclasses.dataclass
    class TestNetObject(NetworkObject):
        network_name = "test_obj"
        object_role = 0

        a: int = 0
        b: int = 0

        @NetworkField(ram_persist=False)
        def set_a(self, item: network_types.int16):
            self.a = item

        @NetworkField
        def set_b(self, item: network_types.int16):
            self.b = item

        def net_create(self) -> None:
            pass

        def net_delete(self) -> None:
            pass

    @dataclasses.dataclass
    class TestNetObjectAI(NetworkObject):
        network_name = "test_obj"
        object_role = 1

        def net_create(self) -> None:
            pass

        def net_delete(self) -> None:
            pass

    tester = FlexibleNetworkObjectTester.create_and_start(
        TestNetObjectAI, TestNetObject
    )
    srv_object = TestNetObjectAI(tester.server)
    srv_object.send_message("set_a", [100])
    srv_object.send_message("set_b", [100])
    srv_object.request_generate()

    client = tester.make_client()
    assert client.managed_objects.get(srv_object.oid) is None
    client.object_manager.request_visible_objects()
    cl_object = client.managed_objects.get(srv_object.oid)
    assert cl_object.a == 0
    assert cl_object.b == 100
