__all__ = ["NetworkObjectRegistry"]

import dataclasses
import json
from typing import TYPE_CHECKING, Any

from magicnet.core import errors
from magicnet.core.net_globals import MNEvents
from magicnet.netobjects.network_object import ForeignNetworkObject, NetworkObject
from magicnet.util.messenger import MessengerNode

if TYPE_CHECKING:
    from magicnet.core.network_manager import NetworkManager


@dataclasses.dataclass
class NetworkObjectRegistry(MessengerNode["NetworkManager", "NetworkManager"]):
    added_classes: list[type[NetworkObject]] = dataclasses.field(default_factory=list)
    foreign_classes: list[type[NetworkObject]] = dataclasses.field(default_factory=list)
    classes: dict[int, type[NetworkObject]] = dataclasses.field(default_factory=dict)
    object_name_to_id: dict[str, int] = dataclasses.field(default_factory=dict)
    initialized: bool = False

    @property
    def manager(self) -> "NetworkManager":
        return self.parent

    def __post_init__(self):
        self.listen(MNEvents.BEFORE_LAUNCH, self.activate)

    def activate(self):
        if self.manager.marshalling_mode:
            self.marshal_all_files()
        elif self.manager.object_signature_filenames:
            self.load_from_filenames()

    def register_object(self, object_type: type[NetworkObject], *, foreign: bool = False):
        if self.initialized:
            raise errors.RegistryObjectAfterInitialization(object_type.__name__)

        if not foreign:
            self.added_classes.append(object_type)
        else:
            self.foreign_classes.append(object_type)

    def marshal_classes(self) -> dict[str, Any]:
        if self.initialized:
            items = self.classes.values()
        else:
            items = self.added_classes

        return {clazz.network_name: clazz.marshal_fields() for clazz in items}

    def unmarshal_foreign_classes(self, items: dict[str, Any]) -> None:
        for key, marshal in items.items():
            clazz = self.classes[self.object_name_to_id[key]]
            clazz.unmarshal_foreign_field(marshal)

    def get_constructor(self, object_type: int) -> type[NetworkObject] | None:
        clazz = self.classes.get(object_type)
        if isinstance(clazz, ForeignNetworkObject):
            return None
        return clazz

    def initialize(self, marshalled_contents: list[dict[str, Any]]):
        if self.initialized:
            raise errors.MultipleRegistryInitializations()

        self.initialized = True
        added_classes = self.added_classes[:]
        foreign_classes = self.foreign_classes[:]

        all_existing_class_names = {clazz.network_name for clazz in added_classes}
        all_class_names = {name for marshal in marshalled_contents for name in marshal}
        all_class_names |= {clazz.network_name for clazz in foreign_classes}
        for foreign_name in all_class_names - all_existing_class_names:
            clazz = ForeignNetworkObject.create_subclass(foreign_name)
            added_classes.append(clazz)
        classes = sorted(added_classes, key=lambda t: t.network_name)
        for idx, clazz in enumerate(classes):
            self.classes[idx] = clazz
            self.object_name_to_id[clazz.network_name] = idx
            clazz.set_type(idx)

        self.added_classes = []
        for item in marshalled_contents:
            self.unmarshal_foreign_classes(item)
        for clazz in foreign_classes:
            local_class = self.classes.get(self.object_name_to_id[clazz.network_name])
            if local_class:
                local_class.add_foreign_class(clazz)
        self.foreign_classes = []
        for clazz in self.classes.values():
            clazz.finalize_fields()

    def load_from_filenames(self):
        if not self.manager.object_signature_filenames:
            return
        items: list[dict[str, Any]] = []
        for file in self.manager.object_signature_filenames:
            with open(file) as f:
                items.append(json.load(f))
        self.initialize(items)

    def marshal_all_files(self):
        assert self.manager.marshalling_mode, "marshalling mode not configured"
        with open(self.manager.marshalling_mode, "w") as f:
            json.dump(self.marshal_classes(), f)
