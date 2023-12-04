__all__ = [
    "DataValidationError",
    "NetworkConnectionError",
    "NetworkConfigurationError",
    "InvalidValidatorArguments",
]


class DataValidationError(TypeError):
    pass


class NetworkConnectionError(OSError):
    pass


class NetworkConfigurationError(ValueError):
    pass


class InvalidValidatorArguments(TypeError):
    def __init__(self, hint):
        super().__init__(f"{hint} is not a valid typehint")


class WrongTupleLength(DataValidationError):
    def __init__(self, length: int, value):
        super().__init__(f"Expected a length {length} tuple, got {value}")


class NoneRequired(DataValidationError):
    def __init__(self, value):
        super().__init__(f"Expected None, got {value}")


class UnionValidationFailed(DataValidationError):
    def __init__(self, value, hint):
        super().__init__(f"Union validation error: expected {hint}, got {value}")


class PredicateValidationFailed(DataValidationError):
    def __init__(self, value, predicate: callable):
        super().__init__(f"{value}: expected {predicate.__name__} to hold")


class TypeComparisonFailed(DataValidationError):
    def __init__(self, origin_type: type, value):
        super().__init__(
            f"{value}: expected {origin_type.__name__}, got {type(value).__name__}"
        )


class RecursiveTypeProvided(DataValidationError):
    def __init__(self, value):
        super().__init__(f"{value}: recursion loop detected")


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
