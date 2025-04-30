__all__ = []

from typing import Any, cast, final

from magicnet.core.net_message import NetMessage
from magicnet.netobjects.network_object import ObjectState
from magicnet.protocol import network_types
from magicnet.protocol.processor_base import MessageProcessor
from magicnet.protocol.protocol_globals import StandardDCReasons
from magicnet.util.messenger import StandardEvents

# https://github.com/microsoft/pyright/issues/10395
uint32 = cast(type[int], network_types.uint32)


@final
class MsgCreateObject(MessageProcessor[int, int, int, int, list[tuple[int, int, list[Any]]]]):
    arg_type = tuple[
        network_types.uint32,  # object ID (without the repository)
        network_types.uint16,  # object type index
        network_types.uint32,  # object owner's repository
        network_types.uint32,  # object zone (unused by default)
        list[tuple[network_types.uint8, network_types.uint8, list[network_types.hashable]]],
        # object's parameters
    ]

    def invoke(self, message: NetMessage[int, int, int, int, list[tuple[int, int, list[Any]]]]):
        assert message.sent_from
        object_id, object_type, owner_id, zone_id, params = message.parameters
        ctor = self.manager.object_registry.get_constructor(object_type)
        if ctor is None:
            message.disconnect_sender(StandardDCReasons.INVALID_OBJECT_TYPE, f"Unknown object: {object_id}")
            return

        success, repo_number = message.sent_from.get_shared_parameter("rp", uint32, disconnect=True)
        if not success or repo_number is None:
            return

        # By default, if 0 is sent the object is owned by its creator
        # This works because repository numbers start from 1
        owner_id = owner_id or repo_number

        obj = ctor(controller=self.manager)
        obj.object_state = ObjectState.GENERATING
        # The repository number is a property of the connection, not the user,
        # so we need to change that here
        object_id += repo_number << 32
        obj.set_parameters(object_id, owner_id, zone_id)
        obj.load_params(message.sent_from, params)
        new_params = obj.get_loaded_params()
        self.manager.object_manager.add_network_object(obj)
        self.manager.object_manager.send_network_object_generate(obj, new_params)
        self.manager.object_manager.initialize_object(obj.oid)


@final
class MsgGenerateObject(MessageProcessor[int, int, int, int]):
    arg_type = tuple[
        network_types.uint64,  # object ID (with the repository)
        network_types.uint16,  # object type index
        network_types.uint32,  # object owner's repository
        network_types.uint32,  # object zone (unused by default)
    ]

    def invoke(self, message: NetMessage[int, int, int, int]):
        assert message.sent_from
        object_id, object_type, owner_id, zone_id = message.parameters
        success, repo_number = message.sent_from.get_shared_parameter("rp", uint32)
        if success and repo_number == object_id >> 32:
            # This means the request was sent from the same handle that handles
            # this response. It is therefore, a partial object!
            # We do a special handling here.
            object_id_base = object_id % (1 << 32)
            obj = self.manager.object_manager.partial_objects.pop(object_id_base, None)
            if not obj or obj.object_state != ObjectState.CREATE_REQUESTED:
                self.emit(
                    StandardEvents.WARNING,
                    f"Ignoring bad partial generation for object {object_id}",
                )
            else:
                obj.object_state = ObjectState.GENERATING
                obj.set_parameters(object_id, owner_id, zone_id)
                self.manager.object_manager.add_network_object(obj)
            return

        ctor = self.manager.object_registry.get_constructor(object_type)
        if ctor is None:
            message.disconnect_sender(StandardDCReasons.INVALID_OBJECT_TYPE, f"Unknown object: {object_id}")
            return

        obj = ctor(controller=self.manager)
        obj.object_state = ObjectState.GENERATING
        obj.set_parameters(object_id, owner_id, zone_id)
        self.manager.object_manager.add_network_object(obj)


@final
class MsgSetObjectField(MessageProcessor[int, int, int, list[Any]]):
    arg_type = tuple[
        network_types.uint64,
        network_types.uint8,
        network_types.uint8,
        list[network_types.hashable],
    ]

    def invoke(self, message: NetMessage[int, int, int, list[Any]]):
        assert message.sent_from
        object_id, role, field, args = message.parameters
        if not (obj := self.manager.net_objects.get(object_id)):
            self.emit(
                StandardEvents.WARNING,
                f"Ignoring invalid set_object_field for object {object_id}",
            )
            return

        obj.call_field(message.sent_from, role, field, args)


@final
class MsgObjectGenerateDone(MessageProcessor[int]):
    arg_type = tuple[network_types.uint64]

    def invoke(self, message: NetMessage[int]):
        self.manager.object_manager.initialize_object(message.parameters[0])


@final
class MsgDeleteObject(MessageProcessor[int]):
    arg_type = tuple[network_types.uint64]

    def invoke(self, message: NetMessage[int]):
        assert message.sent_from
        obj_id = message.parameters[0]
        success, repo_number = message.sent_from.get_shared_parameter("rp", uint32, disconnect=True)
        if not success or repo_number is None:
            return

        self.manager.object_manager.perform_object_deletion(obj_id, repo_number)


@final
class MsgDestroyObject(MessageProcessor[int]):
    arg_type = tuple[network_types.uint64]

    def invoke(self, message: NetMessage[int]):
        obj_id = message.parameters[0]
        self.manager.object_manager.destroy_network_object(obj_id)


@final
class MsgRequestVisible(MessageProcessor[()]):
    arg_type = tuple[()]

    def invoke(self, message: NetMessage[()]):
        assert message.sent_from
        all_objects = self.manager.object_manager.get_visible_objects(message.sent_from)
        for obj in all_objects:
            params = obj.get_loaded_params()
            self.manager.object_manager.send_network_object_generate(obj, params, message.sent_from)
