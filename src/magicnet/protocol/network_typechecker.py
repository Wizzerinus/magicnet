"""
It seems that none of the existing validation libraries can fulfill my usecase.
The closest ones are Pydantic and Typeguard, but unfortunately,
Pydantic lacks support for recursive types in Python below 3.12,
and Typeguard does not work with byte restrictions.
I may extract this into a separate module later.
"""

__all__ = ["check_type"]

from types import UnionType
from typing import (
    Annotated,
    Any,
    ForwardRef,
    Union,
    get_args,
    get_origin,
)

from magicnet.core import errors
from magicnet.protocol import network_types


def check_dict(value, hint, memory):
    args = get_args(hint)
    if not args:
        return
    if len(args) != 2:
        raise errors.InvalidValidatorArguments(hint)
    for k, v in value.items():
        check_type(k, args[0], memory)
        check_type(v, args[1], memory)


def check_list(value, hint, memory):
    args = get_args(hint)
    if not args:
        return
    if len(args) != 1:
        raise errors.InvalidValidatorArguments(hint)
    for it in value:
        check_type(it, args[0], memory)


def check_tuple(value, hint, memory):
    args = get_args(hint)
    if not args:
        return
    match args:
        case ((),):
            if len(value) != 0:
                raise errors.WrongTupleLength(0, value)
        case (*a, b, v) if v is Ellipsis:
            fixed_type_count = len(a)
            if fixed_type_count - 1 > len(value):
                raise errors.WrongTupleLength(fixed_type_count - 1, value)
            for it, arg in zip(value, a, strict=False):
                check_type(it, arg, memory)
            for it in value[fixed_type_count:]:
                check_type(it, b, memory)
        case _:
            if len(value) != len(args):
                raise errors.WrongTupleLength(len(args), value)
            for it, arg in zip(value, args, strict=True):
                check_type(it, arg, memory)


def check_union(value, hint, memory):
    for field in get_args(hint):
        try:
            check_type(value, field, memory)
        except errors.DataValidationError:
            pass
        else:
            return

    raise errors.UnionValidationFailed(value, hint)


def check_none(value, hint, memory):
    if value is not None:
        raise errors.NoneRequired(value)


VALIDATORS = {
    dict: check_dict,
    list: check_list,
    tuple: check_tuple,
    Union: check_union,
    UnionType: check_union,
    None: check_none,
}

SKIP_ISINSTANCE = {Union, UnionType, None}
MUTABLE_TYPES = {dict, list}


def check_predicates(value, metadata):
    for predicate in metadata:
        if callable(predicate) and not predicate(value):
            raise errors.PredicateValidationFailed(value, predicate)


def check_type(value, hint: type[network_types.hashable], memory: dict | None = None):
    origin_type = get_origin(hint) or hint
    meta = None
    if origin_type is Annotated:
        meta = hint.__metadata__
        origin_type = hint.__origin__
    if origin_type is Any:
        if meta is not None:
            check_predicates(value, meta)
        return
    if isinstance(hint, ForwardRef):
        check_type(value, hint.__forward_value__, memory)
        return

    if origin_type not in SKIP_ISINSTANCE and not isinstance(value, origin_type):
        raise errors.TypeComparisonFailed(origin_type, value)

    memory = memory or {}
    if origin_type in MUTABLE_TYPES:
        key = id(value)
        if key in memory:
            raise errors.RecursiveTypeProvided(value)
        memory[key] = 1

    if origin_type in VALIDATORS:
        VALIDATORS[origin_type](value, hint, memory)

    if meta is not None:
        check_predicates(value, meta)
