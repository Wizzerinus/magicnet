import dataclasses
from unittest.mock import MagicMock

from magicnet.core.net_globals import MNEvents
from magicnet.netobjects.network_field import NetworkField
from magicnet.netobjects.network_object import NetworkObject
from magicnet.protocol import network_types
from net_objects.net_tester_netobj import SymmetricNetworkObjectTester


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

        @NetworkField
        def set_value(self, item: MyStruct):
            self.value = item

        def net_create(self) -> None:
            pass

        def net_delete(self) -> None:
            pass

    tester = SymmetricNetworkObjectTester.create_and_start(TestNetObject)
    tester.enable_debug()
    srv_object = TestNetObject(tester.server)
    srv_object.request_generate()

    cl_object = tester.client.managed_objects.get(srv_object.oid)
    assert cl_object.value is None and srv_object.value is None

    srv_object.send_message("set_value", [(1, 2, 3)])
    assert cl_object.value == MyStruct(1, 2, 3)
    srv_object.send_message("set_value", [MyStruct(4, 5, 6)])
    assert cl_object.value == MyStruct(4, 5, 6)
