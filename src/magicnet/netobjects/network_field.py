__all__ = ["NetworkField"]

from typing import Union

from magicnet.core import errors
from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNMathTargets
from magicnet.util.messenger import MessengerNode
from magicnet.util.typechecking.field_signature import FieldSignature


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
