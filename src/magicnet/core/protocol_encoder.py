__all__ = ["ProtocolEncoder"]

import abc
from collections.abc import Iterable

from magicnet.core.net_message import NetMessage


class ProtocolEncoder(abc.ABC):
    """
    ProtocolEncoder is used to encode messages over the wire.
    Unless compatibility with other software is needed,
    one of the encoders in ``magicnet.batteries`` should be used.
    """

    KNOWN_SYMMETRIC = False
    """
    Opt-in setting that allows defining this protocol as symmetric.
    This is usually True, unless some weird cases where the server
    sends data encoded differently from what it expects.
    """

    @abc.abstractmethod
    def pack(self, messages: Iterable[NetMessage]) -> bytes:
        """
        Packs a sequence of messages into a datagram,
        that can be sent through Transport.
        """

    @abc.abstractmethod
    def unpack(self, data: bytes) -> Iterable[NetMessage]:
        """
        Unpacks a datagram received from the server
        into a sequence of individual messages.
        """

    def symmetrize(self) -> "ProtocolEncoder":
        """
        Returns a symmetrized protocol encoder.
        If A.symmetrize() is called, returns B such that
        B.pack(A.unpack(data)) == data for valid data, and
        B.unpack(A.pack(msgs)) == msgs.
        This method can be overridden for complex encoders.
        """

        if self.KNOWN_SYMMETRIC:
            return self
        raise TypeError(f"Invalid attempt to symmetrize {self.__class__.__name__}!")
