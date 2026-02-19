"""Cell-array type."""

from __future__ import annotations

from dataclasses import dataclass, field

from matrace.types.base import AnyType, MatraceType


@dataclass
class CellType(MatraceType):
    """A MATLAB cell array.

    Attributes:
        element_type: The type of the elements contained in the cell array.
            Defaults to :class:`~matrace.types.base.AnyType` (heterogeneous).
        shape: ``(rows, cols)`` dimensions; ``None`` means variable.
    """

    element_type: MatraceType = field(default_factory=AnyType)
    shape: tuple[int | None, int | None] = (None, None)

    def __repr__(self) -> str:
        r = "any" if self.shape[0] is None else str(self.shape[0])
        c = "any" if self.shape[1] is None else str(self.shape[1])
        return f"CellType<{r},{c}>(element={self.element_type!r})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, CellType)
            and self.element_type == other.element_type
            and self.shape == other.shape
        )

    def __hash__(self) -> int:
        return hash((type(self), self.shape))
