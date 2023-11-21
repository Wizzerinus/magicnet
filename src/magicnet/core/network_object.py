__all__ = ["NetworkObject"]

import abc


# Yea this class is not implemented yet, shut up Bugbear
class NetworkObject(abc.ABC):  # noqa: B024
    """
    NetworkObject is used to write messages in an OOP style.
    Each NetworkObject is owned by one of the clients
    (or the server, which also acts like a client),
    with that client controlling an OwnerView of the object,
    while everyone else on the network controls a NetworkView of the object.
    Both of these views allow making network calls to other versions,
    some of which may be caught by middlewares to check auth/etc.
    """
