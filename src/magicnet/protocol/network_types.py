__all__ = []

from typing import Annotated

try:
    from annotated_types import Ge, Lt, MaxLen
except ImportError:
    Ge = lambda t: lambda v: v >= t  # noqa: E731
    Lt = lambda t: lambda v: v < t  # noqa: E731
    MaxLen = lambda t: lambda v: len(v) <= t  # noqa: E731


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
