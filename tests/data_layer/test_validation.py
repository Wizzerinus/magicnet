import dataclasses

from helpers import assert_raises
from magicnet.core.errors import DataValidationError
from magicnet.protocol import network_types
from magicnet.util.typechecking.dataclass_converter import convert_object
from magicnet.util.typechecking.magicnet_typechecker import check_type


def check_validator(validator, good, bad):
    for good_value in good:
        check_type(good_value, validator)
    for bad_value in bad:
        msg = f"Validation succeeded but should have failed: {bad_value}"
        with assert_raises(DataValidationError, msg):
            check_type(bad_value, validator)


def test_validation_base():
    # intX/uintX
    # this one checks that we do validate types, so nothing else needs that check
    check_validator(network_types.uint8, [0, 128, 255], [-1, 256, 1000, "a", [250]])
    check_validator(network_types.int8, [-128, 127], [-129, 128])
    check_validator(network_types.uint16, [0, 65535], [-1, 65536])
    check_validator(network_types.int16, [-32768, 32767], [-32769, 32768])
    check_validator(network_types.uint32, [0, 2**32 - 1], [-1, 2**32])
    check_validator(
        network_types.int32, [-(2**31), 2**31 - 1], [-(2**31) - 1, 2**31]
    )

    # bytes - only checking short ones
    check_validator(network_types.bs16, [b"", b"something"], [b"a" * 17, "a", 10, []])
    check_validator(network_types.s16, ["", "something"], ["a" * 17, b"a", 10, []])


def test_validation_hashable():
    # hashable
    recursive_list = []
    recursive_list.append(recursive_list)
    hashables = [
        0,
        -(2**63),
        2**64 - 1,
        [0, 1, 2, 3, "a"],
        {"a": [1, 2, 3]},
    ]
    unhashables = [
        2**64,
        object(),
        [{"a": object()}],
        recursive_list,
    ]
    check_validator(network_types.hashable, hashables, unhashables)


def test_validation_union():
    our_type = (
        dict[int, int]
        | list[int | str]
        | dict[int, tuple[int]]
        | dict[int, tuple[str, ...]]
    )
    conforming = [
        {1: 2, 3: 4},
        ["a", 1, 2, 3],
        {0: (1,), 2: (4,)},
        {0: ("a", "b", "c"), 1: ("a",)},
    ]
    nonconforming = [
        {1: "a", 3: "b"},
        [[]],
        {1: (2, 3)},
        {1: (2, "3")},
    ]
    check_validator(our_type, conforming, nonconforming)


def test_validation_tuple():
    check_validator(tuple[int, str], [(1, "")], [(1.1, ""), (1, "", "")])
    check_validator(tuple[int, ...], [(1,), (), (1, 2, 3)], [{1: 2}, ("",)])
    check_validator(
        tuple[int, str, ...], [(1,), (1, ""), (1, "", "")], [(1.1, ""), ("", 1)]
    )


def test_validation_dataclass():
    @dataclasses.dataclass
    class A:
        normal_field: int
        default_field: int = 0
        mutable_field: list[int] = dataclasses.field(default_factory=list)

    obj1 = A(1)
    obj2 = A(1, 2)
    obj3 = A(1, 2, [1, 2, 3])
    for obj in (obj1, obj2, obj3):
        assert convert_object(A, dataclasses.astuple(obj)) == obj

    bad = [
        (),
        ("",),
        (1, 2, 3),
        (1, 2, [1, 2, 3], 4),
    ]
    for value in bad:
        msg = f"Validation succeeded but should have failed: {value}"
        with assert_raises(DataValidationError, msg):
            convert_object(A, value)


def test_recursive_conversion():
    @dataclasses.dataclass
    class A:
        value: int

    assert convert_object(A, (1,)) == A(1)
    assert convert_object(list[A], [(1,), A(2)]) == [A(1), A(2)]
    assert convert_object(dict[str, A], {"a": (1,)}) == {"a": A(1)}

    msg = "Validation succeeded but should have failed: (1, 2)"
    with assert_raises(DataValidationError, msg):
        convert_object(list[A], [(1, 2)])

    assert convert_object(tuple, (1, 2)) == (1, 2)

    @dataclasses.dataclass
    class B:
        a: A

    assert convert_object(B, ((1,),)) == B(A(1))
