"""Scalar type – a single numeric or logical value."""

from dataclasses import dataclass

from matrace.types.base import MatraceType
from matrace.types.dtypes import Dtype


@dataclass(frozen=True)
class ScalarType(MatraceType):
    """A single scalar number or logical value.

    Attributes:
        dtype: The numeric kind – ``"float"``, ``"int"``, or ``"logical"``.
    """

    dtype: Dtype = "float"

    def __repr__(self) -> str:
        return f"ScalarType(dtype={self.dtype!r})"
