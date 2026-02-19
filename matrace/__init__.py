"""matrace – MATLAB-to-Python interpreter and compiler.

Type-system and analysis utilities are always available.  The interpreter
(which depends on PyTorch) is loaded lazily so that ``import matrace`` does
not require torch to be installed.
"""

from matrace.analysis.type_parser import (
    FuncAnnotation,
    extract_func_annotations,
    parse_type_str,
)
from matrace.types import (
    AnyType,
    CellType,
    FunctionType,
    MatraceType,
    MatrixType,
    ScalarType,
    StructType,
    VectorType,
)


def __getattr__(name: str):
    if name == "import_matlab_func":
        from matrace.api.import_func import import_matlab_func
        return import_matlab_func
    raise AttributeError(f"module 'matrace' has no attribute {name!r}")
