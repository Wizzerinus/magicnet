__all__ = ["MessengerNode", "StandardEvents"]

import contextlib
import dataclasses
import itertools
from collections.abc import Iterator
from enum import Enum, auto
from typing import Any, Generic, TypeVar
from uuid import uuid4

AnyMessengerNode = TypeVar("AnyMessengerNode", bound="MessengerNode")
MNodeT = TypeVar("MNodeT", bound="MessengerNode")
T = TypeVar("T")


class StandardEvents(Enum):
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    EXCEPTION = auto()
    CHILD_ADDED = auto()
    CHILD_REMOVED = auto()


@dataclasses.dataclass
class CallbackSettings:
    owner: uuid4
    callback: callable
    priority: int = 0


@dataclasses.dataclass
class PriorityDict:
    listeners: dict[int, dict[uuid4, CallbackSettings]] = dataclasses.field(
        default_factory=dict
    )
    priorities: dict[uuid4, int] = dataclasses.field(default_factory=dict)

    def __sort_listeners(self):
        self.listeners = {key: value for key, value in sorted(self.listeners.items())}

    def add(self, owner: uuid4, callback: callable, *, priority: int = 0):
        self.remove(owner)
        if priority not in self.listeners:
            self.listeners[priority] = {}
            self.__sort_listeners()
        self.listeners[priority][owner] = CallbackSettings(owner, callback, priority)
        self.priorities[owner] = priority

    def remove(self, owner: uuid4):
        if owner not in self.priorities:
            return
        prio = self.priorities.pop(owner)
        self.listeners[prio].pop(owner)

    def get_callbacks(self) -> Iterator[CallbackSettings]:
        return itertools.chain.from_iterable(
            per_prio.values() for per_prio in self.listeners.values()
        )


@dataclasses.dataclass
class EventContext:
    sender: "MessengerNode"
    event: Any
    args: tuple
    kwargs: dict


@dataclasses.dataclass
class Listener:
    disabled_uuids: set[uuid4] = dataclasses.field(default_factory=set)
    events: dict[Any, PriorityDict] = dataclasses.field(default_factory=dict)
    event_owners: dict[uuid4, set] = dataclasses.field(default_factory=dict)
    math_targets: dict[Any, PriorityDict] = dataclasses.field(default_factory=dict)
    math_owners: dict[uuid4, set] = dataclasses.field(default_factory=dict)
    contexts: list[EventContext] = dataclasses.field(default_factory=list)

    @staticmethod
    def __add_to_dicts(
        base_dict: dict[Any, PriorityDict],
        owner_dict: dict[uuid4, set],
        owner: uuid4,
        event,
        callback: callable,
        *,
        priority: int = 0,
    ):
        if event not in base_dict:
            base_dict[event] = PriorityDict()
        base_dict[event].add(owner, callback, priority=priority)

        if owner not in owner_dict:
            owner_dict[owner] = set()
        owner_dict[owner].add(event)

    @staticmethod
    def __cleanup(
        base_dict: dict[Any, PriorityDict],
        owner_dict: dict[uuid4, set],
        owner: uuid4,
    ):
        events = owner_dict.pop(owner, None)
        if events:
            for event in events:
                base_dict[event].remove(owner)

    def listen(self, owner: uuid4, event, callback: callable, *, priority: int = 0):
        self.__add_to_dicts(
            self.events,
            self.event_owners,
            owner,
            event,
            callback,
            priority=priority,
        )

    @contextlib.contextmanager
    def set_context(self, context: EventContext):
        try:
            self.contexts.append(context)
            yield
        finally:
            self.contexts.pop()

    @property
    def current_event(self) -> EventContext | None:
        return self.contexts[-1] if self.contexts else None

    def emit(self, sender: AnyMessengerNode, event, *args, **kwargs):
        if event not in self.events:
            return

        with self.set_context(EventContext(sender, event, args, kwargs)):
            for item in self.events[event].get_callbacks():
                if item.owner in self.disabled_uuids:
                    continue
                item.callback(*args, **kwargs)

    def add_math(self, owner: uuid4, event, callback: callable, *, priority: int = 0):
        self.__add_to_dicts(
            self.math_targets,
            self.math_owners,
            owner,
            event,
            callback,
            priority=priority,
        )

    def calculate(self, event, value: T, *args, **kwargs) -> T:
        if event not in self.math_targets:
            return value
        for item in self.math_targets[event].get_callbacks():
            if item.owner in self.disabled_uuids:
                continue
            value = item.callback(value, *args, **kwargs)
        return value

    def ignore_all(self, owner: uuid4):
        self.__cleanup(self.events, self.event_owners, owner)

    def enable(self, owner: uuid4):
        self.disabled_uuids.remove(owner)

    def disable(self, owner: uuid4):
        self.disabled_uuids.add(owner)


@dataclasses.dataclass(kw_only=True, repr=False)
class MessengerNode(Generic[AnyMessengerNode]):
    """
    MessengerNode is a base class for tree-based messaging.
    To use it, first a root node must be created (by calling `create_root`).
    Then other nodes can be attached to the root node
    (through either `create_child` or setting their `parent` value).
    Nodes can be attached recursively as well. After a tree is created,
    calls to listen(), emit(), add_math
    """

    uuid: uuid4 = dataclasses.field(default_factory=uuid4)
    children: dict[Any, AnyMessengerNode] = dataclasses.field(
        default_factory=dict, repr=False
    )
    name: Any = None
    _parent: AnyMessengerNode | None = dataclasses.field(repr=False, default=None)
    _listener: Listener = dataclasses.field(repr=False, default=None)

    @property
    def bound_name(self):
        return self.name if self.name is not None else self.uuid

    @property
    def parent(self) -> AnyMessengerNode:
        return self._parent

    @parent.setter
    def parent(self, new_parent: "MessengerNode"):
        if self._parent:
            self._parent.remove_child(self.bound_name)
        new_parent.add_child(self)

    def __update_parameters__(self, **kwargs):
        pass

    def remove_child(self, name):
        child = self.children.pop(name, None)
        if child:
            self.emit(StandardEvents.CHILD_REMOVED, parent=self, child=child)
            child._parent = None

    def add_child(self, child: "MessengerNode"):
        if child.bound_name in self.children:
            self.emit(
                StandardEvents.WARNING,
                f"Child already exists: {self.uuid=} {child.bound_name=}",
            )
            self.remove_child(child.name)
        self.children[child.bound_name] = child
        child._parent = self
        self.emit(StandardEvents.CHILD_ADDED, parent=self, child=child)

    def create_child(self, ctor: type[MNodeT], name: Any = None, /, **kwargs) -> MNodeT:
        if name is not None and name in self.children:
            current_child = self.children[name]
            if type(current_child) != ctor:
                self.remove_child(name)
            else:
                current_child.__update_parameters__(**kwargs)
                return current_child

        new_child = ctor(name=name, _parent=self, **kwargs)
        self.add_child(new_child)
        return new_child

    @classmethod
    def create_root(cls, **kwargs):
        return cls(_listener=Listener(), **kwargs)

    @property
    def root(self) -> AnyMessengerNode:
        if self.parent is None:
            return self
        return self.parent.root

    @property
    def listener(self) -> Listener:
        root = self.root
        if root is self:
            return self._listener
        return root.listener

    def destroy(self):
        self.listener.ignore_all(self.uuid)
        for child in self.children.values():
            child.destroy()

    def listen(self, event, callback: callable, *, priority: int = 0):
        self.listener.listen(self.uuid, event, callback, priority=priority)

    def emit(self, event, *args, **kwargs):
        if not self.listener:
            return
        self.listener.emit(self, event, *args, **kwargs)

    def add_math_target(self, event, callback: callable, *, priority: int = 0):
        self.listener.add_math(self.uuid, event, callback, priority=priority)

    def calculate(self, event, value: T, *args, **kwargs) -> T:
        return self.listener.calculate(event, value, *args, **kwargs)

    def enable(self, *, recursive: bool = True):
        self.listener.enable(self.uuid)
        if recursive:
            for child in self.children.values():
                child.enable(recursive=recursive)

    def disable(self, *, recursive: bool = True):
        self.listener.disable(self.uuid)
        if recursive:
            for child in self.children.values():
                child.disable(recursive=recursive)
