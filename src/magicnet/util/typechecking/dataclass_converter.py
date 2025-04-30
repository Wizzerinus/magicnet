__all__ = ["convert_object", "unpack_dataclasses"]

import dataclasses
import itertools
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, cast, get_args, get_origin, overload

from magicnet.core import errors
from magicnet.protocol import network_types
from magicnet.util.typechecking.magicnet_typechecker import check_type

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

T = TypeVar("T")

Sentinel = object()


def convert_fields(fields: tuple[dataclasses.Field[object], ...], data: tuple[object, ...]) -> list[type[Any]]:
    output = []
    for field, item in itertools.zip_longest(fields, data, fillvalue=Sentinel):
        if field is Sentinel:
            raise errors.ExcessDataclassValue(item)
        field = cast(dataclasses.Field[object], field)
        if item is Sentinel:
            if field.default is not dataclasses.MISSING:
                item = field.default
            elif field.default_factory is not dataclasses.MISSING:
                item = field.default_factory()
            else:
                raise errors.NoValueProvided(field.name)

        if field.type is Any:
            field_type = network_types.hashable
        else:
            field_type = field.type
        item = convert_object(field_type, item)
        check_type(item, field_type)

        output.append(item)

    return output


def convert_dataclass(typ: type[T], data: tuple[object, ...]) -> T:
    data_ = convert_fields(dataclasses.fields(typ), data)  # pyright: ignore[reportArgumentType]
    return typ(*data_)


def convert_object(hint: type[T], data: Any) -> T:
    args = get_args(hint)
    origin_type = get_origin(hint) or hint
    if origin_type is Annotated:
        origin_type = hint.__origin__

    if origin_type in (tuple, list) and type(data) in (tuple, list):
        if len(args) != 1:
            return data
        return origin_type(convert_object(args[0], item) for item in data)

    if origin_type is dict and isinstance(data, dict):
        if len(args) != 2:
            return data
        return {k: convert_object(args[1], v) for k, v in data.items()}

    if dataclasses.is_dataclass(origin_type) and not dataclasses.is_dataclass(data):
        if not isinstance(data, tuple) and not isinstance(data, list):
            raise errors.TupleOrListRequired(data)
        return convert_dataclass(origin_type, tuple(data))

    return data


@overload
def unpack_dataclasses(data: list[Any]) -> list[Any]: ...


@overload
def unpack_dataclasses(data: tuple[Any, ...]) -> tuple[Any, ...]: ...


@overload
def unpack_dataclasses(data: dict[T, Any]) -> dict[T, Any]: ...


@overload
def unpack_dataclasses(data: "DataclassInstance") -> tuple[Any, ...]: ...


def unpack_dataclasses(data: object):
    if isinstance(data, tuple) or isinstance(data, list):
        return tuple(unpack_dataclasses(item) for item in data)
    if isinstance(data, dict):
        return {k: unpack_dataclasses(v) for k, v in data.items()}
    if dataclasses.is_dataclass(data):
        return tuple(dataclasses.astuple(data))
    return data
