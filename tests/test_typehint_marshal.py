import json
from typing import Any

from magicnet.protocol import network_types
from magicnet.protocol.typehint_marshal import typehint_marshal


def marshal_convert(t):
    marshalled = typehint_marshal.typehint_to_marshal(t)
    jsonned = json.dumps(marshalled)
    unjsonned = json.loads(jsonned)
    return typehint_marshal.marshal_to_typehint(unjsonned)


def check_typehint_identity(t):
    unmarshalled = marshal_convert(t)
    assert t is unmarshalled, f"The type {t} fails to go back"


def check_typehint_equality(t):
    unmarshalled = marshal_convert(t)
    assert t == unmarshalled, f"The type {t} fails to go back"


def test_equal_types():
    check_typehint_identity(dict)
    check_typehint_identity(list)
    check_typehint_identity(int)
    check_typehint_identity(float)
    check_typehint_identity(tuple)
    check_typehint_identity(network_types.hashable)
    check_typehint_identity(Ellipsis)  # required for variable tuples
    check_typehint_identity(Any)

    check_typehint_equality(dict[int, str])
    check_typehint_equality(tuple[int, str, ...])
    check_typehint_equality(dict[int, list[dict[int, str]]])
    check_typehint_equality(str | int)

    check_typehint_equality(network_types.uint8)
    check_typehint_equality(network_types.s16)
    check_typehint_equality(network_types.bs16 | network_types.uint16)
    check_typehint_equality(tuple[network_types.s16, network_types.int32])
