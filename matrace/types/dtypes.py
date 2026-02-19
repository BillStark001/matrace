"""Numeric dtype used by scalar, vector and matrix types."""

from typing import Literal

Dtype = Literal["float", "int", "logical"]

#: All valid dtype strings.
DTYPES: frozenset[str] = frozenset({"float", "int", "logical"})
