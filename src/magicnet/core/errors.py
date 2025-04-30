__all__ = [
    "DataValidationError",
    "NetworkConnectionError",
    "NetworkConfigurationError",
    "ApplicationConfigurationError",
    "ApplicationRuntimeError",
    "InvalidValidatorArguments",
]


from collections.abc import Callable
from typing import Any, ForwardRef


class DataValidationError(TypeError):
    """Failed to validate some data using the runtime type checker"""


class NetworkConnectionError(OSError):
    """Failed to create a socket, connect to the remote socket, etc"""


class NetworkConfigurationError(ValueError):
    """Improperly configured network system"""


class ApplicationConfigurationError(ValueError):
    """Improperly configured application logic"""


class ApplicationRuntimeError(RuntimeError):
    """Part of application handled by MagicNet ceased to work properly"""


class InvalidValidatorArguments(TypeError):
    def __init__(self, hint: type[Any]):
        super().__init__(f"{hint} is not a valid typehint")


class WrongTupleLength(DataValidationError):
    def __init__(self, length: int, value: Any):
        super().__init__(f"Expected a length {length} tuple, got {value}")


class NoneRequired(DataValidationError):
    def __init__(self, value: Any):
        super().__init__(f"Expected None, got {value}")


class TupleOrListRequired(DataValidationError):
    def __init__(self, value: Any):
        super().__init__(f"Expected a tuple or a list, got {value}")


class UnionValidationFailed(DataValidationError):
    def __init__(self, value: Any, hint: type[Any]):
        super().__init__(f"Union validation error: expected {hint}, got {value}")


class PredicateValidationFailed(DataValidationError):
    def __init__(self, value: Any, predicate: Callable[..., Any]):
        super().__init__(f"{value}: expected {predicate.__name__} to hold")


class TypeComparisonFailed(DataValidationError):
    def __init__(self, origin_type: type, value: Any):
        super().__init__(f"{value}: expected {origin_type.__name__}, got {type(value).__name__}")


class RecursiveTypeProvided(DataValidationError):
    def __init__(self, value: Any):
        super().__init__(f"{value}: recursion loop detected")


class NoValueProvided(DataValidationError):
    def __init__(self, name: str):
        super().__init__(f"No value provided for the parameter {name}")


class TooManyArguments(DataValidationError):
    def __init__(self, args: list[Any], signature_count: int):
        super().__init__(f"Too many arguments: {args} (expected {signature_count})")


class ExcessDataclassValue(DataValidationError):
    def __init__(self, value: Any):
        super().__init__(f"Excess dataclass value: {value}")


class DependencyMissing(NetworkConfigurationError):
    def __init__(self, dependency: str, usecase: str):
        super().__init__(f"{dependency} is required to use {usecase}")


class AsymmetricProtocolProvided(NetworkConfigurationError):
    def __init__(self, protocol: str):
        super().__init__(f"Protocol {protocol} cannot be symmetrized")


class ComponentNotProvided(NetworkConfigurationError):
    def __init__(self, component: str):
        super().__init__(f"{component.title()} or {component.lower()} type expected")


class ExtraCallbacksProvided(NetworkConfigurationError):
    def __init__(self):
        super().__init__("All extra callbacks should be outside the standard range")


class ConnectionParametersMissing(NetworkConfigurationError):
    def __init__(self, call_name: str):
        super().__init__(f"{call_name} requires at least one set of parameters")


class UnknownRole(NetworkConfigurationError):
    def __init__(self, role: str):
        super().__init__(f"Unknown role {role}")


class UnnamedField(ApplicationConfigurationError):
    def __init__(self, classname: str):
        super().__init__(f"Network class {classname} has an unnamed field")


class FieldNotInitialized(ApplicationConfigurationError):
    def __init__(self, classname: str, field_name: str):
        super().__init__(f"Network field {classname}.{field_name} is not initialized")


class KeywordOnlyFieldArgument(ApplicationConfigurationError):
    def __init__(self, arg_name: str):
        super().__init__(f"Some network field has a keyword-only argument {arg_name}")


class RegistryObjectAfterInitialization(ApplicationConfigurationError):
    def __init__(self, class_name: str):
        super().__init__(f"{class_name} registered after the registry is finalized")


class MultipleRegistryInitializations(ApplicationConfigurationError):
    def __init__(self):
        super().__init__("The network registry was initialized multiple times")


class InvalidClientRepository(ApplicationConfigurationError):
    def __init__(self, value: int):
        super().__init__(f"Invalid client repository: {value}")


class NoNetworkName(ApplicationConfigurationError):
    def __init__(self, class_name: str):
        super().__init__(f"Class {class_name} has no network name")


class NoObjectRole(ApplicationConfigurationError):
    def __init__(self, class_name: str, network_name: str):
        super().__init__(f"Class {class_name} has no role (net name: {network_name})")


class UnsupportedNetworkType(ApplicationConfigurationError):
    pass


class UnsupportedForwardRef(UnsupportedNetworkType):
    def __init__(self, forward_ref: ForwardRef):
        super().__init__(f"ForwardRef args are currently not supported: {forward_ref}")


class UnsupportedTypehintName(UnsupportedNetworkType):
    def __init__(self, typehint: type[Any]):
        super().__init__(f"The following type is currently not supported: {typehint}")


class UnsupportedAnnotator(UnsupportedNetworkType):
    def __init__(self, func: Callable[..., Any]):
        super().__init__(f"The following annotator is not supported: {func}")


class UnsupportedMarshalledType(UnsupportedNetworkType):
    def __init__(self, nettype: type[Any]):
        super().__init__(f"The following marshal type is not supported: {nettype}")


class ForeignObjectUsed(ApplicationRuntimeError):
    def __init__(self, name: str):
        super().__init__(f"Attempt to use the foreign-only object {name}")


class RepolessClientCreatesNetworkObject(ApplicationRuntimeError):
    def __init__(self, name: str):
        super().__init__(f"Attempt to create an object {name} without a repository")


class UnknownObjectMessage(ApplicationRuntimeError):
    def __init__(self, object_name: str, message: str):
        super().__init__(f"Attempt to call unknown field {object_name}.{message}")


class SenderNotSet(ApplicationRuntimeError):
    def __init__(self, msg: object):
        super().__init__(f"Message {msg} has no sender!")
