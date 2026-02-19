"""Base class for all matrace types."""

from abc import ABC


class MatraceType(ABC):
    """Abstract base class for all matrace types.

    Subclass this to introduce new types into the type system.
    Register a corresponding parser in :data:`matrace.types.registry.TYPE_REGISTRY`
    so the annotation parser can construct your type from a type-string.
    """


class AnyType(MatraceType):
    """Unknown / dynamically-typed value."""

    _instance: "AnyType | None" = None

    def __new__(cls) -> "AnyType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "AnyType()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AnyType)

    def __hash__(self) -> int:
        return hash(type(self))
