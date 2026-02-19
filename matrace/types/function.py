"""Function / callable type."""

from __future__ import annotations

from dataclasses import dataclass, field

from matrace.types.base import MatraceType


@dataclass
class FunctionType(MatraceType):
    """The type of a MATLAB function (or function handle).

    Attributes:
        params: Ordered list of parameter types.
        returns: Ordered list of return-value types.
    """

    params: list[MatraceType] = field(default_factory=list)
    returns: list[MatraceType] = field(default_factory=list)

    def __repr__(self) -> str:
        p = ", ".join(repr(t) for t in self.params)
        r = ", ".join(repr(t) for t in self.returns)
        return f"FunctionType(({p}) -> ({r}))"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FunctionType)
            and self.params == other.params
            and self.returns == other.returns
        )

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.params), tuple(self.returns)))
