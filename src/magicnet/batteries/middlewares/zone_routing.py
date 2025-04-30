import dataclasses
from typing import Any, final

from typing_extensions import Unpack

from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNEvents, MNMathTargets
from magicnet.core.net_message import NetMessage
from magicnet.core.transport_handler import TransportMiddleware
from magicnet.netobjects.network_object import NetworkObject
from magicnet.protocol.protocol_globals import StandardMessageTypes
from magicnet.util.messenger import StandardEvents


@dataclasses.dataclass
@final
class ZoneBasedRouter(TransportMiddleware):
    # NOTE: the current implementation is probably quite slow
    # (this is a heuristic and I don't have any benchmarks, but it would
    #  have to run on a lower level than middlewares to speed it up)

    PROCESSED_MESSAGE_TYPES = {
        StandardMessageTypes.SET_OBJECT_FIELD,
        StandardMessageTypes.GENERATE_OBJECT,
        StandardMessageTypes.OBJECT_GENERATE_DONE,
        StandardMessageTypes.DESTROY_OBJECT,
    }

    def __post_init__(self):
        self.listen(MNEvents.BEFORE_LAUNCH, self.do_before_launch)

    def do_before_launch(self):
        self.add_message_operator(self.validate_message_zone, None)
        self.add_math_target(MNMathTargets.VISIBLE_OBJECTS, self.only_visibles)

    def only_visibles(self, objects: list[NetworkObject], handle: ConnectionHandle) -> list[NetworkObject]:
        success, viszones = handle.get_shared_parameter("vz", list[int])
        if not success or viszones is None:
            self.emit(StandardEvents.WARNING, f"{handle.uuid}: incorrectly set viszones!")
            return []

        vz_set = set(viszones)
        return [obj for obj in objects if obj.zone in vz_set]

    def validate_message_zone(self, message: NetMessage[Unpack[tuple[Any, ...]]], handle: ConnectionHandle):
        if message.message_type not in self.PROCESSED_MESSAGE_TYPES:
            return message

        oid = message.parameters[0]
        obj = self.transport.manager.net_objects.get(oid)
        if obj is None:
            # Strange but ok
            # Note that we still have to do this even if obj is falsey because
            # we might be generating it still
            self.emit(StandardEvents.WARNING, f"Message sent but the object is missing: {oid}")
            return None

        zone = obj.zone
        success, viszones = handle.get_shared_parameter("vz", list[int])
        if not success or viszones is None:
            self.emit(StandardEvents.WARNING, f"{handle.uuid}: incorrectly set viszones!")
            return None

        if zone in viszones:
            return message
        return None
