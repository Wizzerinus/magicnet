import dataclasses

from magicnet.batteries.middlewares.zone_routing import ZoneBasedRouter
from magicnet.netobjects.network_field import NetworkField
from magicnet.netobjects.network_object import NetworkObject
from net_objects.net_tester_netobj import FlexibleNetworkObjectTester


class ZoneTester(FlexibleNetworkObjectTester):
    server_middlewares = [*FlexibleNetworkObjectTester.middlewares, ZoneBasedRouter]


def test_object_zones():
    @dataclasses.dataclass
    class TestNetObject(NetworkObject):
        network_name = "test_obj"
        object_role = 0

        value: int = 0

        @NetworkField
        def set_value(self, value):
            self.value = value

        def net_create(self) -> None:
            pass

        def net_delete(self) -> None:
            pass

    tester = ZoneTester.create_and_start(TestNetObject, TestNetObject)

    first_client = tester.make_client()
    first_client.get_handle("server").set_shared_parameter("vz", [1])
    second_client = tester.make_client()
    second_client.get_handle("server").set_shared_parameter("vz", [2])

    first_object = TestNetObject(tester.server)
    first_object.send_message("set_value", [100])
    first_object.request_generate(zone=1)

    second_object = TestNetObject(tester.server)
    second_object.send_message("set_value", [105])
    second_object.request_generate(zone=2)

    assert first_object.oid not in second_client.net_objects
    assert second_client.net_objects.get(second_object.oid).value == 105
    assert first_client.net_objects.get(first_object.oid).value == 100
    assert second_object.oid not in first_client.net_objects

    first_client.get_handle("server").set_shared_parameter("vz", [2])
    second_client.get_handle("server").set_shared_parameter("vz", [1])
    # Note: invisible object unloading is currently not implemented
    first_client.object_manager.request_visible_objects()
    assert first_client.net_objects.get(second_object.oid).value == 105

    second_object.send_message("set_value", [110])
    assert first_client.net_objects.get(second_object.oid).value == 110
    # we get a discrepancy here because second client no longer sees updates
    assert second_client.net_objects.get(second_object.oid).value == 105
