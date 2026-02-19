"""Vector and matrix types."""

from dataclasses import dataclass
from typing import Literal

from matrace.types.base import MatraceType
from matrace.types.dtypes import Dtype


@dataclass(frozen=True)
class VectorType(MatraceType):
    """A 1-D numeric array (row or column vector).

    Attributes:
        dtype: The numeric kind.
        length: Number of elements, or ``None`` for variable length.
        orientation: ``"row"``, ``"col"``, or ``None`` when not specified.
    """

    dtype: Dtype = "float"
    length: int | None = None
    orientation: Literal["row", "col"] | None = None

    def __repr__(self) -> str:
        parts = []
        if self.length is not None:
            parts.append(str(self.length))
        dim_str = f"<{parts[0]}>" if parts else ""
        orient = f", orientation={self.orientation!r}" if self.orientation else ""
        return f"VectorType{dim_str}(dtype={self.dtype!r}{orient})"


@dataclass(frozen=True)
class MatrixType(MatraceType):
    """A 2-D numeric array.

    Attributes:
        dtype: The numeric kind.
        rows: Number of rows, or ``None`` for variable.
        cols: Number of columns, or ``None`` for variable.
    """

    dtype: Dtype = "float"
    rows: int | None = None
    cols: int | None = None

    def __repr__(self) -> str:
        r = "any" if self.rows is None else str(self.rows)
        c = "any" if self.cols is None else str(self.cols)
        return f"MatrixType<{r},{c}>(dtype={self.dtype!r})"
