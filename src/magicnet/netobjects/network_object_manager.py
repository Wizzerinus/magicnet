__all__ = ["NetworkObjectManager"]

import dataclasses
from typing import TYPE_CHECKING, Any

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNMathTargets
from magicnet.core.net_message import NetMessage
from magicnet.netobjects.network_object import NetworkObject, ObjectState
from magicnet.protocol.protocol_globals import StandardMessageTypes
from magicnet.util.messenger import MessengerNode, StandardEvents

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager


ParameterDefinition = list[tuple[int, int, list[Any]]]


@dataclasses.dataclass
class NetworkObjectManager(MessengerNode["NetworkManager", "NetworkManager"]):
    net_objects: dict[int, NetworkObject] = dataclasses.field(default_factory=dict)
    partial_objects: dict[int, NetworkObject] = dataclasses.field(default_factory=dict)
    """
    Objects that were created on this manager,
    but not yet acknowledged by the remote authority.
    """
    oid_allocator: int = dataclasses.field(init=False, default=0)

    def make_oid(self) -> int:
        self.oid_allocator += 1
        return self.oid_allocator

    @property
    def manager(self) -> "NetworkManager":
        return self.parent

    def add_network_object(self, obj: NetworkObject):
        self.net_objects[obj.oid] = obj

    def send_network_object_generate(
        self,
        obj: NetworkObject,
        fields: ParameterDefinition,
        handle: ConnectionHandle | None = None,
    ):
        msg1 = NetMessage(
            StandardMessageTypes.GENERATE_OBJECT,
            (obj.oid, obj.otype, obj.owner, obj.zone),
        )
        field_messages: list[NetMessage[int, int, int, list[Any]]] = []
        for role, field, params in fields:
            msg = NetMessage(StandardMessageTypes.SET_OBJECT_FIELD, (obj.oid, role, field, params))
            field_messages.append(msg)
        msg2 = NetMessage(StandardMessageTypes.OBJECT_GENERATE_DONE, (obj.oid,))
        for msg in [msg1, *field_messages, msg2]:
            if handle is not None:
                msg.destination = handle
            self.manager.send_message(msg)

    def get_visible_objects(self, handle: ConnectionHandle) -> list[NetworkObject]:
        return self.listener.calculate(MNMathTargets.VISIBLE_OBJECTS, list(self.net_objects.values()), handle)

    def initialize_object(self, obj_id: int):
        if (obj := self.net_objects.get(obj_id)) is None:
            self.emit(StandardEvents.WARNING, f"Unable to init the object {obj_id}!")
            return

        if obj.object_state != ObjectState.GENERATING:
            self.emit(StandardEvents.WARNING, f"The object {obj.oid} is already initialized!")
            return

        obj.net_create()
        obj.object_state = ObjectState.GENERATED

    def destroy_network_object(self, obj_id: int):
        if (obj := self.net_objects.get(obj_id)) is None:
            self.emit(StandardEvents.WARNING, f"Unable to destroy the object {obj_id}!")
            return

        # In case someone has a reference to this
        obj.object_state = ObjectState.INVALID
        obj.net_delete()
        obj.destroy()
        self.net_objects.pop(obj.oid, None)

    def request_delete_object(self, obj_id: int):
        msg = NetMessage(StandardMessageTypes.REQUEST_DELETE_OBJECT, (obj_id,))
        self.manager.send_message(msg)

    def perform_object_deletion(self, obj_id: int, repo_number: int):
        if (obj := self.net_objects.get(obj_id)) is None:
            # we will warn when deleting it locally
            return

        if obj.owner != repo_number:
            # We will never disconnect for this
            # as it may be a result of a race condition
            self.emit(
                StandardEvents.WARNING,
                f"Ignoring unauthorized delete for object {obj.oid} (by {repo_number})",
            )
            return

        msg = NetMessage(StandardMessageTypes.DESTROY_OBJECT, (obj.oid,))
        self.manager.send_message(msg)
        self.destroy_network_object(obj_id)

    def create_object(self, obj: NetworkObject, owner: int = 0):
        """
        Local objects are created on this client and distributed to others.

        Warning: make sure that the network is configured in such a way that
        each client that can execute this call has a preset repository number.
        """

        if self.manager.client_repository is None:
            raise errors.RepolessClientCreatesNetworkObject(obj.network_name)

        obj.oid = self.make_oid() + (self.manager.client_repository << 32)
        obj.owner = owner or self.manager.client_repository
        self.add_network_object(obj)
        self.send_network_object_generate(obj, obj.get_loaded_params())
        obj.object_state = ObjectState.GENERATING
        self.initialize_object(obj.oid)

    def create_remote_object(self, obj: NetworkObject, owner: int = 0):
        """
        Remote objects require a round trip to the authority before creation.

        BIG warning: make sure that the network is configured in such a way that
        each client that can create remote objects can only send the message through
        one handle! Ideally this should be handled as a server-side middleware.
        If multiple connected clients each try to create remote object,
        MagicNet's invariants break and it can no longer guarantee anything.
        """

        obj.oid = self.make_oid()
        self.partial_objects[obj.oid] = obj
        obj.owner = owner
        obj.object_state = ObjectState.CREATE_REQUESTED
        msg = NetMessage(
            StandardMessageTypes.CREATE_OBJECT,
            (obj.oid, obj.otype, owner, obj.zone, obj.get_loaded_params()),
        )
        self.manager.send_message(msg)

    def request_call_field(
        self,
        receiver: ConnectionHandle | None,
        obj: NetworkObject,
        role: int,
        field: int,
        params: list[Any] | tuple[Any, ...],
    ):
        msg = NetMessage(StandardMessageTypes.SET_OBJECT_FIELD, (obj.oid, role, field, params))
        if receiver is not None:
            msg.destination = receiver
        self.manager.send_message(msg)

    def request_visible_objects(self):
        msg = NetMessage(StandardMessageTypes.REQUEST_VISIBLE_OBJECTS)
        self.manager.send_message(msg)
