__all__ = ["typehint_marshal"]

import dataclasses
import inspect
from typing import Annotated, Any, ForwardRef, Union, cast, get_args, get_origin

from magicnet.core import errors
from magicnet.protocol import network_types
from magicnet.util.typechecking.field_signature import FieldSignature, SignatureItem
from magicnet.util.typechecking.magicnet_typechecker import check_type


class TypehintMarshal:
    """
    TypehintMarshal is used to convert FieldSignatures into strings
    and strings back into FieldSignatures.
    It only works with combinations of NetworkTypes, so only useful here.
    TypehintMarshal does not guarantee any kind of backward compatibility,
    as it is quite common to rebuild the marshal set.
    """

    name_to_type = {
        "dict": dict,
        "list": list,
        "tuple": tuple,
        "Union": Union,
        "ell": Ellipsis,
        "any": Any,
        "int": int,
        "float": float,
        "hashable": network_types.hashable,
        "str": str,
        "bytes": bytes,
    }

    annotated_validators: dict[str, type[network_types.AnnotatedValidator]] = {}
    validator_cache: dict[str, network_types.AnnotatedValidator] = {}

    def __init__(self):
        self.add_annotated_validator(network_types.Ge)
        self.add_annotated_validator(network_types.Lt)
        self.add_annotated_validator(network_types.MaxLen)
        self.add_validator(network_types.uint8)
        self.add_validator(network_types.uint16)
        self.add_validator(network_types.uint32)
        self.add_validator(network_types.uint64)
        self.add_validator(network_types.int8)
        self.add_validator(network_types.int16)
        self.add_validator(network_types.int32)
        self.add_validator(network_types.int64)
        self.add_validator(network_types.s16)
        self.add_validator(network_types.s64)
        self.add_validator(network_types.s256)
        self.add_validator(network_types.s4096)
        self.add_validator(network_types.bs16)
        self.add_validator(network_types.bs64)
        self.add_validator(network_types.bs256)
        self.add_validator(network_types.bs4096)

    def add_annotated_validator(self, cls: type[network_types.AnnotatedValidator]):
        self.annotated_validators[cls.__name__] = cls  # type: ignore

    def add_validator(self, subtype: network_types.AnnotatedValidator):
        self.validator_cache[subtype.__name__] = subtype

    def get_annotated_validator(self, data):
        if data in self.validator_cache:
            return self.validator_cache[data]

        validator_name, _, arg = data.partition("(")
        arg = arg[:-1]
        if validator_name not in self.annotated_validators:
            raise errors.UnsupportedMarshalledType(data)
        tbase = self.annotated_validators[validator_name]
        arg_converted = tbase.converter(arg)
        subtype = tbase(arg_converted)
        self.add_validator(subtype)
        return subtype

    def marshal_to_meta(self, item):
        answer = []
        for predicate in item:
            ptype, pdata = predicate["t"], predicate["d"]
            if ptype == "av":
                answer.append(self.get_annotated_validator(pdata))
            elif ptype == "pr":
                answer.append(pdata)
            else:
                raise errors.UnsupportedMarshalledType(predicate)

        return answer

    @staticmethod
    def meta_to_marshal(metadata):
        answer = []
        for predicate in metadata:
            if callable(predicate):
                if not isinstance(predicate, network_types.AnnotatedValidator):
                    raise errors.UnsupportedAnnotator(predicate)

                answer.append({"t": "av", "d": predicate.__name__})
            elif check_type(predicate, network_types.hashable):
                answer.append({"t": "pr", "d": predicate})
            else:
                raise errors.UnsupportedAnnotator(predicate)

        return answer

    def marshal_to_typehint(self, item) -> type:
        tbase, meta, args = item["t"], item["m"], item.get("a", ())
        if tbase not in self.name_to_type:
            raise errors.UnsupportedTypehintName(tbase)
        tbase = self.name_to_type[tbase]
        args = [self.marshal_to_typehint(x) for x in args]
        if args:
            our_type = tbase[*args]
        else:
            our_type = tbase

        if meta is not None:
            our_type = Annotated[our_type, *self.marshal_to_meta(meta)]
        return our_type

    def typehint_to_marshal(self, hint: type[network_types.hashable]):
        if hint is Ellipsis:
            return {"t": "ell", "m": None}

        origin_type = get_origin(hint) or hint
        meta = None
        if origin_type is Annotated:
            meta = hint.__metadata__
            origin_type = arg_wielder = hint.__origin__
        else:
            arg_wielder = hint
        meta = self.meta_to_marshal(meta) if meta is not None else None

        if hint is network_types.hashable:
            return {"t": "hashable", "m": meta}
        if isinstance(hint, ForwardRef):
            raise errors.UnsupportedForwardRef(hint)
        if origin_type is Any:
            return {"t": "any", "m": meta}

        args = [self.typehint_to_marshal(t) for t in get_args(arg_wielder)]
        origin_name = origin_type.__name__
        if origin_name == "UnionType":
            origin_name = "Union"
        return {"t": origin_name, "m": meta, "a": args}

    def marshal_to_item(self, marshal) -> SignatureItem:
        data = SignatureItem(**marshal)
        data.typehint = self.marshal_to_typehint(marshal["typehint"])
        return data

    def item_to_marshal(self, item: SignatureItem):
        data = cast(dict[str, network_types.hashable], dataclasses.asdict(item))
        if item.default_value is inspect.Parameter.empty:
            del data["default_value"]
        data["typehint"] = self.typehint_to_marshal(item.typehint)
        return data

    def marshal_to_signature(self, marshal: network_types.hashable) -> FieldSignature:
        items = [self.marshal_to_item(x) for x in marshal["f"]]
        fs = FieldSignature()
        fs.set_name(marshal["n"])
        fs.set_from_list(items, marshal["a"])
        return fs

    def signature_to_marshal(self, signature: FieldSignature) -> network_types.hashable:
        return {
            "f": [self.item_to_marshal(x) for x in signature.signature],
            "n": signature.name,
            "a": int(signature.flags),
        }


typehint_marshal = TypehintMarshal()
