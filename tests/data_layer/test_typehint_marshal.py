import json
from typing import Any

from magicnet.netobjects.network_field import NetworkField
from magicnet.protocol import network_types
from magicnet.util.typechecking.field_signature import SignatureFlags
from magicnet.util.typechecking.typehint_marshal import typehint_marshal


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


def test_annotated():
    @NetworkField
    def some_function(
        a: int, b: network_types.int8, c: network_types.uint8 = 0, *d: str
    ):
        pass

    marshalled = typehint_marshal.signature_to_marshal(some_function)
    jsonned = json.dumps(marshalled)
    unjsonned = json.loads(jsonned)
    signature = typehint_marshal.marshal_to_signature(unjsonned)

    _, err = signature.validate_arguments([1, 2, 3, "a", "b", "c"])
    assert err is None
    _, err = signature.validate_arguments([1, 200, 3, "a", "b", "c"])
    assert "Lt(128)" in str(err)
    _, err = signature.validate_arguments([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert "got int" in str(err)
    _, err = signature.validate_arguments([1])
    assert "No value" in str(err)
    _, err = signature.validate_arguments([1, 2])
    assert err is None
    _, err = signature.validate_arguments([1, 2, 3])
    assert err is None

    assert signature.flags == SignatureFlags.PERSIST_IN_RAM

    @NetworkField(ram_persist=False)
    def some_field():
        pass

    marshalled = typehint_marshal.signature_to_marshal(some_field)
    jsonned = json.dumps(marshalled)
    unjsonned = json.loads(jsonned)
    signature = typehint_marshal.marshal_to_signature(unjsonned)
    assert signature.flags == SignatureFlags(0)
