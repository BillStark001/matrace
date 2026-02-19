"""Tests for Phase 2.1 (type hierarchy) and Phase 2.2 (JSDoc annotation parser).

These tests are deliberately kept free of ``torch`` at import time so that
the type-system and parser tests can run in any environment.  Only the
``TestImportWithAnnotations`` class needs ``torch``; it skips automatically
when the package is absent.
"""

from __future__ import annotations

import pytest

# --------------------------------------------------------------------------
# matrace.types and matrace.analysis.type_parser do NOT depend on torch.
# --------------------------------------------------------------------------
from matrace.types import (
    AnyType,
    CellType,
    FunctionType,
    MatrixType,
    ScalarType,
    StructType,
    VectorType,
)
from matrace.analysis.type_parser import (
    FuncAnnotation,
    extract_func_annotations,
    parse_type_str,
)


# ==========================================================================
# 2.1 – Type hierarchy
# ==========================================================================


class TestAnyType:
    def test_singleton(self):
        assert AnyType() is AnyType()

    def test_equality(self):
        assert AnyType() == AnyType()

    def test_not_equal_to_scalar(self):
        assert AnyType() != ScalarType()

    def test_repr(self):
        assert repr(AnyType()) == "AnyType()"

    def test_is_matrace_type(self):
        from matrace.types.base import MatraceType
        assert isinstance(AnyType(), MatraceType)


class TestScalarType:
    def test_default_dtype(self):
        assert ScalarType().dtype == "float"

    def test_explicit_dtypes(self):
        assert ScalarType(dtype="int").dtype == "int"
        assert ScalarType(dtype="logical").dtype == "logical"

    def test_equality_same(self):
        assert ScalarType("float") == ScalarType("float")

    def test_equality_different_dtype(self):
        assert ScalarType("float") != ScalarType("int")

    def test_hashable(self):
        s = {ScalarType("float"), ScalarType("int"), ScalarType("float")}
        assert len(s) == 2

    def test_frozen(self):
        t = ScalarType("float")
        with pytest.raises((AttributeError, TypeError)):
            t.dtype = "int"  # type: ignore[misc]


class TestVectorType:
    def test_defaults(self):
        v = VectorType()
        assert v.dtype == "float"
        assert v.length is None
        assert v.orientation is None

    def test_fixed_length(self):
        assert VectorType(dtype="int", length=5).length == 5

    def test_zero_length(self):
        assert VectorType(length=0).length == 0

    def test_orientation_row(self):
        assert VectorType(orientation="row").orientation == "row"

    def test_orientation_col(self):
        assert VectorType(orientation="col").orientation == "col"

    def test_equality_same(self):
        assert VectorType("float", 3) == VectorType("float", 3)

    def test_equality_different_length(self):
        assert VectorType("float", 3) != VectorType("float", 4)

    def test_equality_different_dtype(self):
        assert VectorType("float", 3) != VectorType("int", 3)

    def test_equality_different_orientation(self):
        assert VectorType("float", 3, "row") != VectorType("float", 3, "col")

    def test_hashable(self):
        s = {VectorType("float", 3), VectorType("int", None), VectorType("float", 3)}
        assert len(s) == 2


class TestMatrixType:
    def test_defaults(self):
        m = MatrixType()
        assert m.rows is None and m.cols is None and m.dtype == "float"

    def test_fixed_shape(self):
        m = MatrixType(dtype="float", rows=3, cols=4)
        assert m.rows == 3 and m.cols == 4

    def test_one_by_one(self):
        m = MatrixType(rows=1, cols=1)
        assert m.rows == 1 and m.cols == 1

    def test_variable_rows_fixed_cols(self):
        m = MatrixType(rows=None, cols=5)
        assert m.rows is None and m.cols == 5

    def test_equality_same(self):
        assert MatrixType("float", 3, 3) == MatrixType("float", 3, 3)

    def test_equality_different_cols(self):
        assert MatrixType("float", 3, 3) != MatrixType("float", 3, 4)

    def test_equality_different_dtype(self):
        assert MatrixType("float", 3, 3) != MatrixType("int", 3, 3)

    def test_hashable(self):
        s = {MatrixType("float", 3, 3), MatrixType("int", None, None),
             MatrixType("float", 3, 3)}
        assert len(s) == 2


class TestCellType:
    def test_default_element_is_any(self):
        assert isinstance(CellType().element_type, AnyType)

    def test_nested_scalar(self):
        c = CellType(element_type=ScalarType("float"))
        assert isinstance(c.element_type, ScalarType)
        assert c.element_type.dtype == "float"

    def test_nested_matrix(self):
        c = CellType(element_type=MatrixType("float", 3, 3))
        assert isinstance(c.element_type, MatrixType)

    def test_equality_same(self):
        assert CellType(ScalarType("float")) == CellType(ScalarType("float"))

    def test_equality_different_element(self):
        assert CellType(ScalarType("float")) != CellType(ScalarType("int"))

    def test_default_shape(self):
        assert CellType().shape == (None, None)


class TestStructType:
    def test_empty_fields(self):
        assert StructType().fields == {}

    def test_single_field(self):
        s = StructType(fields={"x": ScalarType("float")})
        assert "x" in s.fields
        assert isinstance(s.fields["x"], ScalarType)

    def test_multiple_fields(self):
        s = StructType({"x": ScalarType("float"), "A": MatrixType("float", 3, 3)})
        assert set(s.fields.keys()) == {"x", "A"}

    def test_equality_same(self):
        a = StructType({"x": ScalarType("float")})
        b = StructType({"x": ScalarType("float")})
        assert a == b

    def test_equality_different_value(self):
        assert StructType({"x": ScalarType("float")}) != StructType({"x": ScalarType("int")})

    def test_equality_different_keys(self):
        assert StructType({"x": ScalarType()}) != StructType({"y": ScalarType()})


class TestFunctionType:
    def test_empty(self):
        f = FunctionType()
        assert f.params == [] and f.returns == []

    def test_signature(self):
        f = FunctionType(
            params=[ScalarType("float"), MatrixType("float", 3, 3)],
            returns=[MatrixType("float", 3, 3)],
        )
        assert len(f.params) == 2 and len(f.returns) == 1

    def test_equality_same(self):
        a = FunctionType([ScalarType()], [ScalarType()])
        b = FunctionType([ScalarType()], [ScalarType()])
        assert a == b

    def test_equality_different_params(self):
        assert (FunctionType([ScalarType("float")], [])
                != FunctionType([ScalarType("int")], []))

    def test_equality_different_returns(self):
        assert (FunctionType([], [ScalarType("float")])
                != FunctionType([], [ScalarType("int")]))


# ==========================================================================
# 2.2 – Type-string parser: valid inputs
# ==========================================================================


class TestParseTypeStr:

    # -- any ----------------------------------------------------------------

    def test_any(self):
        assert parse_type_str("any") == AnyType()

    def test_any_whitespace(self):
        assert parse_type_str("  any  ") == AnyType()

    # -- scalar -------------------------------------------------------------

    def test_scalar_float(self):
        assert parse_type_str("scalar float") == ScalarType("float")

    def test_scalar_int(self):
        assert parse_type_str("scalar int") == ScalarType("int")

    def test_scalar_logical(self):
        assert parse_type_str("scalar logical") == ScalarType("logical")

    def test_scalar_extra_whitespace(self):
        assert parse_type_str("  scalar   float  ") == ScalarType("float")

    # -- vector -------------------------------------------------------------

    def test_vector_no_dim(self):
        t = parse_type_str("vector float")
        assert isinstance(t, VectorType)
        assert t.length is None and t.dtype == "float"

    def test_vector_fixed_dim(self):
        t = parse_type_str("vector<3> float")
        assert isinstance(t, VectorType) and t.length == 3

    def test_vector_large_dim(self):
        t = parse_type_str("vector<1000> int")
        assert t.length == 1000

    def test_vector_zero_dim(self):
        t = parse_type_str("vector<0> float")
        assert t.length == 0

    def test_vector_any_dim(self):
        t = parse_type_str("vector<any> float")
        assert isinstance(t, VectorType) and t.length is None

    def test_vector_logical(self):
        assert parse_type_str("vector logical").dtype == "logical"

    # -- matrix -------------------------------------------------------------

    def test_matrix_no_dims(self):
        t = parse_type_str("matrix float")
        assert isinstance(t, MatrixType)
        assert t.rows is None and t.cols is None

    def test_matrix_fixed(self):
        t = parse_type_str("matrix<3,3> float")
        assert t.rows == 3 and t.cols == 3

    def test_matrix_any_any(self):
        t = parse_type_str("matrix<any,any> float")
        assert t.rows is None and t.cols is None

    def test_matrix_fixed_any(self):
        t = parse_type_str("matrix<5,any> int")
        assert t.rows == 5 and t.cols is None and t.dtype == "int"

    def test_matrix_any_fixed(self):
        t = parse_type_str("matrix<any,4> float")
        assert t.rows is None and t.cols == 4

    def test_matrix_one_by_one(self):
        t = parse_type_str("matrix<1,1> float")
        assert t.rows == 1 and t.cols == 1

    def test_matrix_large_dims(self):
        t = parse_type_str("matrix<1000,2000> int")
        assert t.rows == 1000 and t.cols == 2000

    def test_matrix_logical(self):
        assert parse_type_str("matrix<2,2> logical").dtype == "logical"

    # -- cell ---------------------------------------------------------------

    def test_cell_bare(self):
        t = parse_type_str("cell")
        assert isinstance(t, CellType)
        assert isinstance(t.element_type, AnyType)

    def test_cell_any_explicit(self):
        t = parse_type_str("cell<any>")
        assert isinstance(t, CellType)
        assert isinstance(t.element_type, AnyType)

    def test_cell_scalar_element(self):
        t = parse_type_str("cell<scalar float>")
        assert isinstance(t.element_type, ScalarType)
        assert t.element_type.dtype == "float"

    def test_cell_matrix_element(self):
        t = parse_type_str("cell<matrix<3,3> float>")
        assert isinstance(t.element_type, MatrixType)
        assert t.element_type.rows == 3

    def test_cell_vector_element(self):
        t = parse_type_str("cell<vector<any> float>")
        assert isinstance(t.element_type, VectorType)

    def test_cell_nested_cell(self):
        t = parse_type_str("cell<cell<scalar float>>")
        assert isinstance(t, CellType)
        assert isinstance(t.element_type, CellType)
        assert isinstance(t.element_type.element_type, ScalarType)

    def test_cell_of_struct(self):
        t = parse_type_str("cell<struct<{x: scalar float}>>")
        assert isinstance(t, CellType)
        assert isinstance(t.element_type, StructType)

    # -- struct -------------------------------------------------------------

    def test_struct_single_field(self):
        t = parse_type_str("struct<{x: scalar float}>")
        assert isinstance(t, StructType)
        assert set(t.fields) == {"x"}
        assert isinstance(t.fields["x"], ScalarType)

    def test_struct_two_fields(self):
        t = parse_type_str("struct<{x: scalar float, y: scalar int}>")
        assert set(t.fields) == {"x", "y"}
        assert t.fields["x"].dtype == "float"
        assert t.fields["y"].dtype == "int"

    def test_struct_nested_matrix_and_vector(self):
        t = parse_type_str("struct<{A: matrix<2,2> float, b: vector<any> float}>")
        assert isinstance(t.fields["A"], MatrixType)
        assert isinstance(t.fields["b"], VectorType)

    def test_struct_empty(self):
        t = parse_type_str("struct<{}>")
        assert isinstance(t, StructType)
        assert t.fields == {}

    def test_struct_field_cell_value(self):
        t = parse_type_str("struct<{data: cell<scalar float>}>")
        assert isinstance(t.fields["data"], CellType)

    def test_struct_field_nested_struct(self):
        t = parse_type_str("struct<{inner: struct<{z: scalar float}>}>")
        assert isinstance(t.fields["inner"], StructType)

    # -- round-trip equality ------------------------------------------------

    def test_roundtrip_scalar(self):
        assert parse_type_str("scalar float") == ScalarType("float")

    def test_roundtrip_matrix(self):
        assert parse_type_str("matrix<3,3> float") == MatrixType("float", 3, 3)

    def test_roundtrip_vector(self):
        assert parse_type_str("vector<5> int") == VectorType("int", 5)

    def test_roundtrip_cell(self):
        assert parse_type_str("cell<scalar int>") == CellType(ScalarType("int"))

    def test_roundtrip_struct(self):
        assert (
            parse_type_str("struct<{x: scalar float}>")
            == StructType({"x": ScalarType("float")})
        )

    def test_roundtrip_any(self):
        assert parse_type_str("any") is AnyType()


# ==========================================================================
# 2.2 – Type-string parser: invalid / error inputs
# ==========================================================================


class TestParseTypeStrErrors:

    def test_empty_string(self):
        with pytest.raises(ValueError):
            parse_type_str("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError):
            parse_type_str("   ")

    def test_unknown_type_keyword(self):
        with pytest.raises(ValueError, match="Unknown type keyword"):
            parse_type_str("tensor float")

    def test_dtype_alone_is_unknown(self):
        # "float" is a dtype, not a type keyword
        with pytest.raises(ValueError, match="Unknown type keyword"):
            parse_type_str("float")

    def test_scalar_missing_dtype(self):
        with pytest.raises(ValueError):
            parse_type_str("scalar")

    def test_scalar_bad_dtype(self):
        with pytest.raises(ValueError, match="dtype"):
            parse_type_str("scalar double")

    def test_vector_missing_dtype(self):
        with pytest.raises(ValueError):
            parse_type_str("vector<3>")

    def test_vector_bad_dtype(self):
        with pytest.raises(ValueError, match="dtype"):
            parse_type_str("vector<3> real")

    def test_matrix_bad_dtype(self):
        with pytest.raises(ValueError, match="dtype"):
            parse_type_str("matrix<3,3> double")

    def test_matrix_missing_closing_bracket(self):
        with pytest.raises(ValueError):
            parse_type_str("matrix<3,3 float")

    def test_matrix_missing_second_dim(self):
        with pytest.raises(ValueError):
            parse_type_str("matrix<3> float")

    def test_matrix_non_numeric_dim(self):
        with pytest.raises(ValueError):
            parse_type_str("matrix<x,3> float")

    def test_struct_trailing_comma(self):
        # Trailing comma is tolerated: the parser consumes the comma then
        # finds '}' and exits the field loop cleanly.
        t = parse_type_str("struct<{x: scalar float,}>")
        assert isinstance(t, StructType)
        assert list(t.fields.keys()) == ["x"]

    def test_struct_missing_colon(self):
        with pytest.raises(ValueError):
            parse_type_str("struct<{x scalar float}>")

    def test_struct_missing_outer_brackets(self):
        with pytest.raises(ValueError):
            parse_type_str("struct<x: scalar float>")

    def test_struct_missing_lt(self):
        with pytest.raises(ValueError):
            parse_type_str("struct{x: scalar float}")

    def test_trailing_tokens_after_type(self):
        with pytest.raises(ValueError):
            parse_type_str("scalar float extra")

    def test_integer_alone(self):
        with pytest.raises(ValueError):
            parse_type_str("3")


# ==========================================================================
# 2.2 – Annotation extraction from MATLAB source
# ==========================================================================

# Helper: parse MATLAB source and return (Function_Definition, source)
def _parse_func(source: str):
    from matrace.parser.parser import parse_matlab_code
    cu = parse_matlab_code(source, "test.m")
    return cu.l_functions[0], source


class TestExtractFuncAnnotations:

    # -- basic tagging ------------------------------------------------------

    def test_param_and_returns(self):
        src = (
            "% @param {scalar float} x - Input\n"
            "% @returns {scalar float} - Output\n"
            "function y = foo(x)\n"
            "  y = x + 1;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert "x" in ann.params
        assert isinstance(ann.params["x"], ScalarType)
        assert ann.params["x"].dtype == "float"
        assert len(ann.returns) == 1
        assert isinstance(ann.returns[0], ScalarType)

    def test_return_no_description(self):
        src = (
            "% @returns {scalar float}\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert len(ann.returns) == 1
        assert isinstance(ann.returns[0], ScalarType)

    def test_return_alias_no_s(self):
        """@return (without trailing 's') is accepted."""
        src = (
            "% @return {scalar float}\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert len(ann.returns) == 1

    # -- multiple params / returns -----------------------------------------

    def test_multiple_params(self):
        src = (
            "% @param {matrix<3,3> float} A\n"
            "% @param {vector<any> float} b\n"
            "% @returns {matrix<any,any> float}\n"
            "function x = solve(A, b)\n"
            "  x = A;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert isinstance(ann.params["A"], MatrixType) and ann.params["A"].rows == 3
        assert isinstance(ann.params["b"], VectorType) and ann.params["b"].length is None
        assert isinstance(ann.returns[0], MatrixType)

    def test_multiple_returns(self):
        src = (
            "% @returns {scalar float}\n"
            "% @returns {scalar int}\n"
            "function [a, b] = two()\n"
            "  a = 1; b = 2;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert len(ann.returns) == 2
        assert ann.returns[0].dtype == "float"
        assert ann.returns[1].dtype == "int"

    # -- type diversity -----------------------------------------------------

    def test_cell_param(self):
        src = (
            "% @param {cell<scalar float>} C\n"
            "% @returns {scalar float}\n"
            "function s = sum_cells(C)\n"
            "  s = 0;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert isinstance(ann.params["C"], CellType)
        assert isinstance(ann.params["C"].element_type, ScalarType)

    def test_struct_param(self):
        src = (
            "% @param {struct<{x: scalar float, y: scalar float}>} pt\n"
            "function r = norm_pt(pt)\n"
            "  r = 0;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert isinstance(ann.params["pt"], StructType)
        assert "x" in ann.params["pt"].fields and "y" in ann.params["pt"].fields

    def test_any_param(self):
        src = (
            "% @param {any} val\n"
            "function y = f(val)\n"
            "  y = val;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert isinstance(ann.params["val"], AnyType)

    # -- no annotations -----------------------------------------------------

    def test_no_annotations(self):
        src = (
            "function y = bare(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert ann.params == {}
        assert ann.returns == []

    def test_regular_comment_no_tags(self):
        src = (
            "% This function does something useful.\n"
            "% It has no type annotations.\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert ann.params == {} and ann.returns == []

    # -- robustness ---------------------------------------------------------

    def test_malformed_type_skipped(self):
        src = (
            "% @param {BADTYPE unknown_dtype} x\n"
            "% @returns {scalar float}\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert ann.params == {}          # malformed @param silently skipped
        assert len(ann.returns) == 1     # valid @returns still parsed

    def test_malformed_returns_skipped(self):
        src = (
            "% @param {scalar float} x\n"
            "% @returns {BADTYPE bad_dtype}\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert "x" in ann.params         # valid @param still parsed
        assert ann.returns == []         # malformed @returns silently skipped

    def test_param_overwritten_by_later_same_name(self):
        """When the same parameter name appears twice, the last wins."""
        src = (
            "% @param {scalar float} x\n"
            "% @param {scalar int} x\n"    # overwrites the float annotation
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert ann.params["x"].dtype == "int"

    # -- whitespace and case ------------------------------------------------

    def test_tag_case_insensitive_param(self):
        src = (
            "% @PARAM {scalar float} x\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert "x" in ann.params

    def test_tag_case_insensitive_returns(self):
        src = (
            "% @RETURNS {scalar float}\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert len(ann.returns) == 1

    def test_extra_spaces_in_type_braces(self):
        src = (
            "% @param {  scalar  float  } x\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert isinstance(ann.params.get("x"), ScalarType)

    # -- comment proximity --------------------------------------------------

    def test_blank_line_between_comments_and_function(self):
        """Blank lines do not break the comment search upward."""
        src = (
            "% @param {scalar float} x\n"
            "\n"                           # blank line
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert "x" in ann.params

    def test_non_comment_line_breaks_search(self):
        """A non-comment, non-blank line above the function is a hard boundary."""
        src = (
            "% @param {scalar float} x\n"
            "y = 0;\n"                     # code line – stops upward search
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert ann.params == {}   # comment is not adjacent (blocked by code)

    def test_function_at_top_of_file(self):
        """Function with no preceding lines produces empty annotations."""
        src = (
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        fd, content = _parse_func(src)
        ann = extract_func_annotations(fd, content)
        assert ann.params == {} and ann.returns == []

    # -- multi-function file ------------------------------------------------

    def test_second_function_in_file(self):
        """Annotations for the second function in a file are isolated."""
        src = (
            "% @param {scalar float} a\n"
            "function b = first(a)\n"
            "  b = a;\n"
            "end\n"
            "\n"
            "% @param {matrix<3,3> float} M\n"
            "% @returns {scalar float}\n"
            "function r = second(M)\n"
            "  r = 0;\n"
            "end\n"
        )
        fd, content = _parse_func(src)  # returns first function only
        ann = extract_func_annotations(fd, content)
        assert "a" in ann.params
        assert "M" not in ann.params    # 'M' belongs to second function

        from matrace.parser.parser import parse_matlab_code
        cu = parse_matlab_code(src, "test.m")
        fd2 = cu.l_functions[1]
        ann2 = extract_func_annotations(fd2, content)
        assert "M" in ann2.params
        assert isinstance(ann2.params["M"], MatrixType)
        assert ann2.params["M"].rows == 3
        assert len(ann2.returns) == 1


# ==========================================================================
# Integration: import_matlab_func with return_ast=True
# ==========================================================================

class TestImportWithAnnotations:
    """Needs torch – skipped automatically when torch is absent."""

    def test_return_ast_includes_annotation(self):
        torch = pytest.importorskip("torch")  # noqa: F841 – skip without torch
        from matrace.api.import_func import import_matlab_func

        src = (
            "% @param {scalar float} x\n"
            "% @returns {scalar float}\n"
            "function y = f(x)\n"
            "  y = x;\n"
            "end\n"
        )
        ast_node, annotation, func = import_matlab_func(
            src, is_code=True, return_ast=True
        )
        assert isinstance(annotation, FuncAnnotation)
        assert "x" in annotation.params
        assert isinstance(annotation.params["x"], ScalarType)
        assert len(annotation.returns) == 1


# ==========================================================================
# Extensibility: custom type via TYPE_REGISTRY
# ==========================================================================

class TestTypeRegistry:

    def test_register_and_parse(self):
        from dataclasses import dataclass
        from matrace.types.base import MatraceType
        from matrace.types.registry import TYPE_REGISTRY, register_type_parser

        @dataclass(frozen=True)
        class TensorType(MatraceType):
            rank: int = 0

        def _parse_tensor(parser):
            parser.consume("LT")
            rank = int(parser.consume("INT")[1])
            parser.consume("GT")
            return TensorType(rank=rank)

        register_type_parser("tensor", _parse_tensor)
        try:
            t = parse_type_str("tensor<3>")
            assert isinstance(t, TensorType)
            assert t.rank == 3
        finally:
            del TYPE_REGISTRY["tensor"]

    def test_duplicate_registration_same_fn_ok(self):
        """Re-registering the same function is idempotent."""
        from matrace.types.registry import TYPE_REGISTRY, register_type_parser

        def _dummy(parser):
            return AnyType()

        register_type_parser("_dup_test", _dummy)
        register_type_parser("_dup_test", _dummy)   # same fn – should not raise
        del TYPE_REGISTRY["_dup_test"]

    def test_duplicate_registration_different_fn_raises(self):
        """Re-registering with a *different* function must raise."""
        from matrace.types.registry import TYPE_REGISTRY, register_type_parser

        def _fn_a(parser): return AnyType()
        def _fn_b(parser): return AnyType()

        register_type_parser("_dup2_test", _fn_a)
        try:
            with pytest.raises(ValueError, match="already registered"):
                register_type_parser("_dup2_test", _fn_b)
        finally:
            del TYPE_REGISTRY["_dup2_test"]

