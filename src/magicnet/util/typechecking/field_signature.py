__all__ = ["SignatureItem", "FieldSignature", "SignatureFlags"]


import dataclasses
import inspect
from collections.abc import Callable
from enum import IntFlag, auto
from typing import Any, Union

from magicnet.core import errors
from magicnet.protocol import network_types
from magicnet.util.typechecking.dataclass_converter import convert_object
from magicnet.util.typechecking.magicnet_typechecker import check_type

NoValueProvided = object()
"""Sentinel for data validation when there's no argument in the slot"""


class SignatureFlags(IntFlag):
    PERSIST_IN_RAM = auto()


@dataclasses.dataclass
class SignatureItem:
    name: str
    typehint: type
    is_variadic: bool
    default_value: Any = inspect.Parameter.empty

    def __repr__(self):
        desc = f"{self.name}: {self.typehint}"
        if self.is_variadic:
            return f"*{desc}"
        return desc

    def validate_value(self, value, *, on_call_site: bool = False):
        if value is NoValueProvided:
            if self.is_variadic:
                return NoValueProvided
            if self.default_value is inspect.Parameter.empty:
                raise errors.NoValueProvided(self.name)
            value = self.default_value

        typehint = self.typehint
        if typehint is Any and on_call_site:
            typehint = network_types.hashable

        # raises if something is wrong
        value = convert_object(self.typehint, value)  # type: ignore
        check_type(value, typehint)

        return value

    @classmethod
    def convert_annotation(cls, annotation) -> type:
        if annotation is inspect.Parameter.empty:
            return Any
        return annotation

    @classmethod
    def from_parameter(cls, parameter: inspect.Parameter) -> Union["SignatureItem", None]:
        if parameter.name in ("cls", "self"):
            # don't care about class instance
            return None

        if parameter.kind == parameter.VAR_KEYWORD:
            # We do not allow keyword variadics (**kwargs),
            # so the receiver site receives no parameters there
            return None
        if parameter.kind == parameter.KEYWORD_ONLY:
            # Same thing here as keyword variadics,
            # except there may not be a default value at all, which is bad
            if parameter.default == parameter.empty:
                raise errors.KeywordOnlyFieldArgument(parameter.name)
            return None

        return SignatureItem(
            parameter.name,
            cls.convert_annotation(parameter.annotation),
            parameter.kind == parameter.VAR_POSITIONAL,
            parameter.default,
        )

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> list["SignatureItem"]:
        output = []
        for item in signature.parameters.values():
            converted = cls.from_parameter(item)
            if converted:
                output.append(converted)
        return output


class FieldSignature:
    signature: list[SignatureItem] = None
    name: str = None
    flags: SignatureFlags = SignatureFlags(0)

    def __repr__(self):
        return f"{self.name}{self.signature}"

    def set_from_callable(self, field: Callable[..., Any], flags: SignatureFlags):
        self.signature = SignatureItem.from_signature(inspect.signature(field))
        self.flags = flags

    def set_from_list(self, data: list[SignatureItem], flags: int):
        self.signature = data
        self.flags = SignatureFlags(flags)

    def set_name(self, name: str):
        self.name = name

    def validate_arguments(self, args: list[Any], *, on_call_site: bool = False):
        parameters: list[Any] = []
        try:
            variadic_param: SignatureItem | None = None
            for i in range(max(len(args), len(self.signature))):
                value = args[i] if i < len(args) else NoValueProvided
                signature = self.signature[i] if i < len(self.signature) else variadic_param
                if signature is None:
                    raise errors.TooManyArguments(args, len(self.signature))
                # raises if something is wrong
                value = signature.validate_value(value, on_call_site=on_call_site)
                if value is not NoValueProvided:
                    parameters.append(value)
                if signature.is_variadic:
                    variadic_param = signature
        except errors.DataValidationError as e:
            return None, e

        return parameters, None
