__all__ = ["NetworkField", "SignatureItem", "FieldSignature"]

import dataclasses
import inspect
from typing import Any, Union

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNMathTargets
from magicnet.protocol import network_types
from magicnet.protocol.network_typechecker import check_type
from magicnet.util.messenger import MessengerNode

NoValueProvided = object()
"""Sentinel for data validation when there's no argument in the slot"""


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
        if value is NoValueProvided and self.default_value is inspect.Parameter.empty:
            raise errors.NoValueProvided(self.name)

        typehint = self.typehint
        if typehint is Any and on_call_site:
            typehint = network_types.hashable

        # raises if something is wrong
        check_type(value, typehint)

    @classmethod
    def convert_annotation(cls, annotation) -> type:
        if annotation is inspect.Parameter.empty:
            return Any
        return annotation

    @classmethod
    def from_parameter(
        cls, parameter: inspect.Parameter
    ) -> Union["SignatureItem", None]:
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

    def __repr__(self):
        return f"{self.name}{self.signature}"

    def set_from_callable(self, field: callable):
        self.signature = SignatureItem.from_signature(inspect.signature(field))

    def set_from_list(self, data: list[SignatureItem]):
        self.signature = data

    def set_name(self, name: str):
        self.name = name

    def validate_arguments(self, args: list, *, on_call_site: bool = False):
        try:
            variadic_param: SignatureItem | None = None
            for i in range(max(len(args), len(self.signature))):
                value = args[i] if i < len(args) else NoValueProvided
                signature = (
                    self.signature[i] if i < len(self.signature) else variadic_param
                )
                if signature is None:
                    raise errors.TooManyArguments(args, len(self.signature))
                # raises if something is wrong
                signature.validate_value(value, on_call_site=on_call_site)
                if signature.is_variadic:
                    variadic_param = signature
        except errors.DataValidationError as e:
            return e

        return None


class NetworkField(FieldSignature):
    field_call: callable = None

    def __init__(self, callback: Union[callable, None] = None, **kwargs):  # noqa: UP007
        self.args = kwargs
        if callback is not None:
            self(callback)

    def __call__(self, field: callable):
        self.field_call = field
        self.set_from_callable(field)
        return self

    def call(self, obj, params):
        self.field_call(obj, *params)

    def check_validity(self, classname: str):
        if self.name is None:
            raise errors.UnnamedField(classname)

        if self.field_call is None:
            raise errors.FieldNotInitialized(classname, self.name)

    def validate_handle(self, obj: MessengerNode, handle: ConnectionHandle):
        # By default all calls are allowed, override the math target to change
        return obj.calculate(MNMathTargets.FIELD_CALL_ALLOWED, 1, self, handle)
