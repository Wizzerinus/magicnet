__all__ = ["NetworkObjectMeta"]

import abc
from typing import TYPE_CHECKING, cast

from magicnet.netobjects.network_field import NetworkField

if TYPE_CHECKING:
    from magicnet.netobjects.network_object import NetworkObject


class NetworkFieldCounter(dict):
    field_data: list[NetworkField]

    def __init__(self):
        super().__init__()
        self.field_data = []

    def __setitem__(self, key, value):
        if isinstance(value, NetworkField):
            value.set_name(key)
            self.field_data.append(value)

        super().__setitem__(key, value)


class NetworkObjectMeta(abc.ABCMeta):
    """
    Internal detail of the NetworkObject's implementation.
    """

    @classmethod
    def __prepare__(cls, name, bases):
        return NetworkFieldCounter()

    def __new__(cls, name, bases, classdict: NetworkFieldCounter):
        for field in classdict.field_data:
            # Raises if something is wrong
            field.check_validity(name)

        result = cast(
            type["NetworkObject"], type.__new__(cls, name, bases, dict(classdict))
        )
        result.field_data = classdict.field_data
        result.foreign_field_data = {}
        return result
