__all__ = ["AnnotatedValidator", "Ge", "Lt", "MaxLen"]

import abc
import sys
from collections.abc import Callable
from typing import Annotated, Any, ClassVar, ForwardRef


class AnnotatedValidator(abc.ABC):
    converter: ClassVar[Callable[[str], Any]] = str

    def __init__(self, arg):
        self.arg = arg

    @property
    def __name__(self):
        return f"{self.__class__.__name__}({self.arg})"

    def __repr__(self):
        return self.__name__

    @abc.abstractmethod
    def __call__(self, value):
        pass

    def __eq__(self, other):
        return type(other) is type(self) and other.arg == self.arg

    def __hash__(self):
        return hash(self.__name__)


class Ge(AnnotatedValidator):
    converter = int

    def __call__(self, value):
        return value >= self.arg


class Lt(AnnotatedValidator):
    converter = int

    def __call__(self, value):
        return value < self.arg


class MaxLen(AnnotatedValidator):
    converter = int

    def __call__(self, value):
        return len(value) <= self.arg


uint8 = Annotated[int, Ge(0), Lt(2**8)]
uint16 = Annotated[int, Ge(0), Lt(2**16)]
uint32 = Annotated[int, Ge(0), Lt(2**32)]
uint64 = Annotated[int, Ge(0), Lt(2**64)]

int8 = Annotated[int, Ge(-(2**7)), Lt(2**7)]
int16 = Annotated[int, Ge(-(2**15)), Lt(2**15)]
int32 = Annotated[int, Ge(-(2**31)), Lt(2**31)]
int64 = Annotated[int, Ge(-(2**63)), Lt(2**63)]

s16 = Annotated[str, MaxLen(2**4)]
bs16 = Annotated[bytes, MaxLen(2**4)]
s64 = Annotated[str, MaxLen(2**6)]
bs64 = Annotated[bytes, MaxLen(2**6)]
s256 = Annotated[str, MaxLen(2**8)]
bs256 = Annotated[bytes, MaxLen(2**8)]
s4096 = Annotated[str, MaxLen(2**12)]
bs4096 = Annotated[bytes, MaxLen(2**12)]

primitive = uint64 | int64 | str | bytes

# Note: we have to use these classes due to PEP-585 being cringe
# And also some more cringe to ensure the types are evaluated
_fr_h = ForwardRef("hashable")
hashable = uint64 | int64 | str | bytes | list[_fr_h] | dict[primitive, _fr_h] | tuple[_fr_h, ...]

if sys.version_info >= (3, 12, 4):
    _fr_h._evaluate(globals(), locals(), frozenset(), recursive_guard=frozenset())  # noqa
else:
    _fr_h._evaluate(globals(), locals(), frozenset())  # noqa
