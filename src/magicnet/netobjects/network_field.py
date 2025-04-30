__all__ = ["NetworkField"]

from collections.abc import Callable
from typing import Any, final

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNMathTargets
from magicnet.util.messenger import MessengerNode
from magicnet.util.typechecking.field_signature import FieldSignature, SignatureFlags


@final
class NetworkField(FieldSignature):
    field_call: Callable[..., Any] | None = None

    def __init__(
        self,
        callback: Callable[..., Any] | None = None,  # noqa: UP007
        *,
        ram_persist: bool = True,
        **kwargs: object,
    ):
        self.ram_persist = ram_persist
        self.args = kwargs
        if callback is not None:
            self(callback)

    def make_flags(self) -> SignatureFlags:
        value = SignatureFlags(0)
        if self.ram_persist:
            value |= SignatureFlags.PERSIST_IN_RAM
        return value

    def __call__(self, field: Callable[..., Any]):
        self.field_call = field
        self.set_from_callable(field, self.make_flags())
        return self

    def call(self, obj: Any, params: Any):
        assert self.field_call is not None
        self.field_call(obj, *params)

    def check_validity(self, classname: str):
        if self.field_call is None:
            raise errors.FieldNotInitialized(classname, self.name)

    def validate_handle(self, obj: MessengerNode[Any, Any], handle: ConnectionHandle):
        # By default all calls are allowed, override the math target to change
        return obj.calculate(MNMathTargets.FIELD_CALL_ALLOWED, 1, self, handle)
