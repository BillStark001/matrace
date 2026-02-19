"""Public surface of the matrace type system.

All concrete type classes and the :data:`AnyType` singleton are importable
directly from ``matrace.types``.
"""

from matrace.types.base import AnyType, MatraceType
from matrace.types.cell import CellType
from matrace.types.dtypes import DTYPES, Dtype
from matrace.types.function import FunctionType
from matrace.types.matrix import MatrixType, VectorType
from matrace.types.registry import TYPE_REGISTRY, register_type_parser
from matrace.types.scalar import ScalarType
from matrace.types.struct import StructType

__all__ = [
    "MatraceType",
    "AnyType",
    "ScalarType",
    "VectorType",
    "MatrixType",
    "CellType",
    "StructType",
    "FunctionType",
    "Dtype",
    "DTYPES",
    "TYPE_REGISTRY",
    "register_type_parser",
]
