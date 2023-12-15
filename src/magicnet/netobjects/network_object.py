__all__ = ["NetworkObject", "ObjectState", "ForeignNetworkObject"]

import abc
import dataclasses
from collections import defaultdict
from enum import IntEnum, auto
from typing import TYPE_CHECKING, ClassVar

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNEvents
from magicnet.netobjects.network_field import NetworkField
from magicnet.netobjects.network_object_meta import NetworkObjectMeta
from magicnet.util.messenger import MessengerNode, StandardEvents
from magicnet.util.typechecking.dataclass_converter import unpack_dataclasses
from magicnet.util.typechecking.field_signature import FieldSignature
from magicnet.util.typechecking.typehint_marshal import typehint_marshal

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager

ParameterDefinition = list[tuple[int, int, list]]


class ObjectState(IntEnum):
    INVALID = auto()
    """The object is not initialized yet or is destroyed"""
    CREATE_REQUESTED = auto()
    """The generation datagram was sent from this client"""
    GENERATING = auto()
    """The object's fields are being set during generation"""
    GENERATED = auto()
    """The object's net_create() was called and it is ready to use"""


@dataclasses.dataclass
class MarshalledSignature:
    object_role: int
    signatures: list


@dataclasses.dataclass
class NetworkObject(MessengerNode, abc.ABC, metaclass=NetworkObjectMeta):
    """
    NetworkObject is used to write messages in an OOP style.
    Each NetworkObject has a view on one or more servers,
    and allows sending messages to the other views.
    Some of the messages may be caught by middlewares to check auth/etc.
    """

    controller: "NetworkManager" = dataclasses.field(repr=False)

    oid: int = 0
    otype: ClassVar[int] = 0
    owner: int = 0
    zone: int = 0

    object_role: ClassVar[int] = None
    """
    Each object exists in one or more roles.
    For example, a set of roles may look like (client = 0, server = 1, owner = 2)
    (although the NetworkObject class itself does not define such a set).
    This number indicates the role of the current view.
    Each role has a number of fields that it can receive.
    Each client knows the callbacks of its own role, but only knows the signatures
    of all foreign roles (which are required to get the correct callback # etc).
    All calls to the fields owned by the wrong role are ignored.
    Different object types can have different role mappings.
    """

    network_name: ClassVar[str] = None
    """
    The network name of this class. All views of the same object type
    must have the same network name.
    """

    loaded_params: dict[tuple[int, int], list] = dataclasses.field(default_factory=dict)
    field_data: ClassVar[list[NetworkField]] = None
    """Contains the list of all fields, is set automatically by the metaclass."""
    foreign_field_data: ClassVar[dict[int, list[FieldSignature]]] = None
    """Contains the list of all foreign fields, is set automatically."""
    message_index: ClassVar[dict[str, tuple[int, int]]] = None

    object_state: ObjectState = ObjectState.INVALID

    def __post_init__(self):
        self.parent = self.controller.object_manager

    @classmethod
    def set_type(cls, otype: int) -> None:
        cls.otype = otype

    @classmethod
    def marshal_fields(cls) -> dict:
        return dataclasses.asdict(
            MarshalledSignature(
                cls.object_role,
                [
                    typehint_marshal.signature_to_marshal(field)
                    for field in cls.field_data
                ],
            )
        )

    @classmethod
    def unmarshal_foreign_field(cls, data: dict) -> None:
        signature = MarshalledSignature(**data)
        if signature.object_role == cls.object_role:
            # we don't need to marshal our own fields
            # this is so that multiple roles each can load the full set of files
            return
        cls.foreign_field_data[signature.object_role] = [
            typehint_marshal.marshal_to_signature(field)
            for field in signature.signatures
        ]

    @classmethod
    def add_foreign_class(cls, foreign: type["NetworkObject"]) -> None:  # noqa: UP006
        cls.foreign_field_data[foreign.object_role] = foreign.field_data

    @classmethod
    def finalize_fields(cls) -> None:
        if cls.network_name is None:
            raise errors.NoNetworkName(cls.__name__)

        if cls.object_role is None:
            raise errors.NoObjectRole(cls.__name__, cls.network_name)

        cls.message_index = {}
        all_fields: dict[int, list[str]] = defaultdict(list)
        for field in cls.field_data:
            all_fields[cls.object_role].append(field.name)
        for role, foreign_data in cls.foreign_field_data.items():
            for field in foreign_data:
                all_fields[role].append(field.name)

        for role, fields in all_fields.items():
            for idx, field in enumerate(fields):
                cls.message_index[field] = (role, idx)

    def __bool__(self):
        return self.object_state != ObjectState.INVALID

    def set_parameters(self, oid: int, owner: int, zone: int):
        self.owner = owner
        self.zone = zone
        self.oid = oid

    @property
    def author_repository(self) -> int:
        return self.oid >> 32

    @property
    def manager(self) -> "NetworkManager":
        return self.parent.parent

    def load_params(self, handle: ConnectionHandle, params: ParameterDefinition):
        for role_id, field_id, arguments in params:
            self.call_field(handle, role_id, field_id, arguments)

    def get_loaded_params(self) -> ParameterDefinition:
        return [
            (role, field, params)
            for (role, field), params in self.loaded_params.items()
        ]

    def resolve_callback_name(self, field_id: int) -> NetworkField | None:
        if field_id >= len(self.field_data):
            return None
        return self.field_data[field_id]

    def call_field(
        self, handle: ConnectionHandle, role_id: int, field_id: int, arguments: list
    ):
        if role_id != self.object_role:
            # calling a remote field, we only save the parameter
            self.loaded_params[(role_id, field_id)] = arguments
            return

        field = self.resolve_callback_name(field_id)
        if field is None:
            self.emit(
                StandardEvents.WARNING,
                f"Attempt to call unknown field {field_id} on class {self.otype}!",
            )
            self.emit(
                MNEvents.BAD_NETWORK_OBJECT_CALL,
                dict(obj=self, handle=handle, field_id=field_id, reason="no-field"),
            )
            return

        if not field.validate_handle(self, handle):
            self.emit(
                StandardEvents.WARNING,
                f"Unauthorized attempt to call field {field.name}!",
            )
            self.emit(
                MNEvents.BAD_NETWORK_OBJECT_CALL,
                dict(obj=self, handle=handle, field_id=field_id, reason="no-auth"),
            )
            return

        arguments, e = field.validate_arguments(arguments)
        if e:
            self.emit(
                StandardEvents.WARNING, f"Arguments for {field.name} do not match: {e}"
            )
            self.emit(
                MNEvents.BAD_NETWORK_OBJECT_CALL,
                dict(
                    obj=self,
                    handle=handle,
                    field_id=field_id,
                    reason="bad-args",
                    msg=str(e),
                ),
            )
            return

        self.loaded_params[(role_id, field_id)] = arguments
        field.call(self, arguments)

    def request_generate(self, owner: int = 0) -> None:
        if self.manager.client_repository is not None:
            # We have authority, we can create any objects
            # or at least try to do it
            self.manager.object_manager.create_object(self, owner)
        else:
            self.manager.object_manager.create_remote_object(self, owner)

    def request_delete(self) -> None:
        if self.manager.client_repository is not None:
            # We have authority, we can delete anyone's objects
            # or at least try to do it
            self.manager.object_manager.perform_object_deletion(self.oid, self.owner)
        else:
            self.manager.object_manager.request_delete_object(self.oid)

    def resolve_field(self, message: str) -> tuple[int, int]:
        if message not in self.message_index:
            raise errors.UnknownObjectMessage(self.network_name, message)
        return self.message_index[message]

    def send_message(self, message: str, args: list | tuple = ()) -> None:
        args = unpack_dataclasses(args)
        role_id, field_id = self.resolve_field(message)
        self.loaded_params[(role_id, field_id)] = list(args)
        if self.object_state == ObjectState.GENERATED:
            self.manager.object_manager.request_call_field(
                self, role_id, field_id, args
            )

    @abc.abstractmethod
    def net_create(self) -> None:
        """
        Performs the procedures to initialize the object's view,
        after all of its fields supplied during initialization
        were filled already.
        """

    @abc.abstractmethod
    def net_delete(self) -> None:
        """
        Performs procedures to delete the object's view from the application.
        This does not have to do things like removing listeners etc.,
        which will be done by the manager itself.
        """


@dataclasses.dataclass
class ForeignNetworkObject(NetworkObject):
    """
    ForeignNetworkObject represents a network object type that is not
    used on the current role. For example, an object may only exist
    on the server side and not be used on the client. In that case,
    the client will have this class in its registry. Instances
    of this class may not be created! This class only exists to ensure
    that all servers/clients have the same object ID mapping.
    Note that MagicNet does not itself manage messages to prevent creation
    of these objects, which has to be done through a separate middleware instead.
    """

    @staticmethod
    def create_subclass(name: str) -> type[NetworkObject]:
        clazz = type(f"Foreign{name}", (ForeignNetworkObject,), {})
        clazz.network_name = name
        return clazz  # type: ignore

    def __post_init__(self):
        raise errors.ForeignObjectUsed(self.network_name)

    def net_create(self):
        raise errors.ForeignObjectUsed(self.network_name)

    def net_delete(self):
        raise errors.ForeignObjectUsed(self.network_name)

    @classmethod
    def unmarshal_foreign_field(cls, data: dict) -> None:
        # We need not do this operation, as this facet will not
        # receive or send any messages anyway if configured properly
        pass

    @classmethod
    def finalize_fields(cls) -> None:
        # We need not do this operation, as this facet will not
        # receive or send any messages anyway if configured properly
        pass
