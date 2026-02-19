"""Struct type."""

from __future__ import annotations

from dataclasses import dataclass, field

from matrace.types.base import MatraceType


@dataclass
class StructType(MatraceType):
    """A MATLAB structure with named fields.

    Attributes:
        fields: Mapping from field name to its :class:`MatraceType`.
    """

    fields: dict[str, MatraceType] = field(default_factory=dict)

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}: {v!r}" for k, v in self.fields.items())
        return f"StructType({{{inner}}})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StructType) and self.fields == other.fields

    def __hash__(self) -> int:
        return hash((type(self), tuple(sorted(self.fields.keys()))))
