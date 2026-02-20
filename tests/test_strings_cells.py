"""Tests for bugs #9, #10, #17, #22, #23, #24.

Coverage:
* Bug #9/#10 – string / char-array handling and concatenation
* Bug #17    – switch statement (SWITCH_ENTRY/EXIT/ACTION), break/continue/return
              in CFG executor, NotImplementedError for unknown literal types
* Bug #22    – mixed cell/matrix operations (cell expansion with C{:})
* Bug #23    – nested cell indexing (C{1}{1}{1})
* Bug #24    – dynamic struct field access (read and write via s.(fieldname))
"""

import pytest
import torch

from matrace.api.import_func import import_matlab_func
from matrace.stdlib.structs import create_struct

# ---------------------------------------------------------------------------
# Shared scope helpers
# ---------------------------------------------------------------------------

_STRUCT_SCOPE = {'struct': create_struct}

# ---------------------------------------------------------------------------
# Load MATLAB fixtures at module level (import errors surface immediately)
# ---------------------------------------------------------------------------

f_string = import_matlab_func('./tests/matlab_examples/string_ops.m')
f_cell   = import_matlab_func('./tests/matlab_examples/cell_ops.m')
f_switch = import_matlab_func('./tests/matlab_examples/switch_ops.m')
f_dyn    = import_matlab_func('./tests/matlab_examples/dyn_field.m',
                               scope=_STRUCT_SCOPE)


# ===========================================================================
# Bug #9 / #10 — string support and char/string distinction
# ===========================================================================

class TestStringSupport:
    """Bug #9: string concatenation; Bug #10: char-array/string literals."""

    def test_string_concat(self):
        """[s1 ' ' s2] produces the expected concatenated string."""
        r1, _, _, _ = f_string('hello', 'world')
        assert r1 == 'hello world'

    def test_passthrough(self):
        """Assigning a char-array variable preserves the string value."""
        _, r2, _, _ = f_string('hello', 'world')
        assert r2 == 'hello'

    def test_double_quoted_literal(self):
        """Double-quoted string literal ("hello") is a Python str."""
        _, _, r3, _ = f_string('hello', 'world')
        assert isinstance(r3, str)
        assert r3 == 'hello'

    def test_single_quoted_literal(self):
        """Single-quoted char-array literal ('world') is a Python str."""
        _, _, _, r4 = f_string('hello', 'world')
        assert isinstance(r4, str)
        assert r4 == 'world'

    def test_string_concat_inline(self):
        """Inline concatenation of three char arrays."""
        code = (
            "function r = concat3(a, b, c)\n"
            "  r = [a '-' b '-' c];\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        assert f('x', 'y', 'z') == 'x-y-z'

    def test_unknown_literal_raises(self):
        """expr_literal raises NotImplementedError for unsupported literal types."""
        from matrace.interpreter.executor import expr_literal
        # Passing a non-Literal node should raise NotImplementedError
        class FakeLiteral:
            pass
        with pytest.raises(NotImplementedError):
            expr_literal(FakeLiteral())


# ===========================================================================
# Bug #17 — missing AST node handlers (switch, break, continue, return)
# ===========================================================================

class TestSwitchStatement:
    """Bug #17: switch statement now routes correctly."""

    def test_case_1_matches(self):
        r1, _, _, _ = f_switch(torch.tensor([[1.]]), 'x')
        assert r1.item() == 10

    def test_case_2_matches(self):
        r1, _, _, _ = f_switch(torch.tensor([[2.]]), 'x')
        assert r1.item() == 20

    def test_otherwise_matches(self):
        """When no case matches, otherwise clause is taken."""
        r1, _, _, _ = f_switch(torch.tensor([[99.]]), 'x')
        assert r1.item() == 0

    def test_no_match_no_otherwise_fallthrough(self):
        """Switch with no otherwise and no matching case leaves variable unchanged."""
        _, r2, _, _ = f_switch(torch.tensor([[1.]]), 'x')
        # r2 is pre-set to 99; the inner switch case 99 does NOT match x=1
        assert r2.item() == 99

    def test_switch_no_match_sets_value(self):
        """When case 99 matches, r2 is updated to 1."""
        _, r2, _, _ = f_switch(torch.tensor([[99.]]), 'x')
        assert r2.item() == 1

    def test_string_switch_foo(self):
        _, _, r3, _ = f_switch(torch.tensor([[0.]]), 'foo')
        assert r3.item() == 1

    def test_string_switch_bar(self):
        _, _, r3, _ = f_switch(torch.tensor([[0.]]), 'bar')
        assert r3.item() == 2

    def test_string_switch_otherwise(self):
        _, _, r3, _ = f_switch(torch.tensor([[0.]]), 'baz')
        assert r3.item() == 0

    def test_cell_case_first_group(self):
        """case {1, 2} matches when x is 1 or 2."""
        _, _, _, r4 = f_switch(torch.tensor([[1.]]), 'x')
        assert r4.item() == 100
        _, _, _, r4 = f_switch(torch.tensor([[2.]]), 'x')
        assert r4.item() == 100

    def test_cell_case_second_group(self):
        """case {3, 4} matches when x is 3 or 4."""
        _, _, _, r4 = f_switch(torch.tensor([[3.]]), 'x')
        assert r4.item() == 200

    def test_cell_case_otherwise(self):
        _, _, _, r4 = f_switch(torch.tensor([[10.]]), 'x')
        assert r4.item() == 0


class TestBreakContinueReturn:
    """Bug #17: break and return CFG nodes are handled correctly."""

    def test_break_exits_loop_early(self):
        code = (
            "function r = test_break()\n"
            "  r = 0;\n"
            "  for i = 1:10\n"
            "    if i == 3\n"
            "      break;\n"
            "    end\n"
            "    r = r + i;\n"
            "  end\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        # i=1 and i=2 contribute; i=3 triggers break
        assert f().item() == pytest.approx(3.0)

    def test_return_exits_function_early(self):
        code = (
            "function r = test_return(x)\n"
            "  r = 0;\n"
            "  if x > 0\n"
            "    r = 1;\n"
            "    return;\n"
            "  end\n"
            "  r = 99;\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        assert f(torch.tensor([[5.]])).item() == pytest.approx(1.0)
        assert f(torch.tensor([[-1.]])).item() == pytest.approx(99.0)


# ===========================================================================
# Bug #22 — cell expansion [C{:}] into a matrix
# ===========================================================================

class TestCellExpansion:
    """Bug #22: C{:} expands all cell elements for use in [...] context."""

    def test_explicit_element_concat(self):
        """[E{1}, E{2}] concatenates two matrices from a cell."""
        _, _, _, _, r5 = f_cell()
        assert torch.equal(r5, torch.tensor([[1, 2, 3, 4]]))

    def test_colon_expansion(self):
        """[E{:}] expands all elements and concatenates them."""
        code = (
            "function r = expand()\n"
            "  E = {[1 2], [3 4]};\n"
            "  r = [E{:}];\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        assert torch.equal(f(), torch.tensor([[1, 2, 3, 4]]))

    def test_scalar_cell_expansion(self):
        """[C{:}] with scalar cell elements gives a row vector."""
        code = (
            "function r = scalars()\n"
            "  C = {10, 20, 30};\n"
            "  r = [C{:}];\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        result = f()
        assert result.numel() == 3
        vals = result.flatten().tolist()
        assert vals == pytest.approx([10.0, 20.0, 30.0])


# ===========================================================================
# Bug #23 — nested cell indexing
# ===========================================================================

class TestNestedCellIndexing:
    """Bug #23: C{i} works and can be chained for nested cells."""

    def test_linear_index_first(self):
        r1, _, _, _, _ = f_cell()
        assert r1 == 10

    def test_linear_index_second(self):
        _, r2, _, _, _ = f_cell()
        assert r2 == 20

    def test_two_index(self):
        """D{2,1} returns element at row 2, col 1."""
        _, _, r3, _, _ = f_cell()
        assert r3 == 3

    def test_nested_one_level(self):
        """N{1}{1} accesses the single element of a nested cell."""
        _, _, _, r4, _ = f_cell()
        assert r4 == 42

    def test_triple_nesting(self):
        """C{1}{1}{1} works for three levels of nesting."""
        code = (
            "function r = triple()\n"
            "  C = {{{99}}};\n"
            "  r = C{1}{1}{1};\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        assert f() == 99

    def test_cell_assignment(self):
        """C{1} = val updates the cell element in place."""
        code = (
            "function r = assign_cell()\n"
            "  C = {1, 2, 3};\n"
            "  C{2} = 99;\n"
            "  r = C{2};\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True)
        assert f() == 99


# ===========================================================================
# Bug #24 — dynamic struct field access
# ===========================================================================

class TestDynamicFieldAccess:
    """Bug #24: s.(fieldname) read and write works correctly."""

    def test_dynamic_write_and_read(self):
        """Write to s.(field) and read it back."""
        r1, _ = f_dyn('x', 42)
        assert r1 == 42

    def test_static_field_updated_by_dynamic_write(self):
        """Dynamic write to 'x' is visible via static read s.x."""
        _, r2 = f_dyn('x', 99)
        assert r2 == 99

    def test_dynamic_field_different_name(self):
        """Writing to a new dynamic field works."""
        code = (
            "function r = new_field(name, val)\n"
            "  s = struct('a', 0);\n"
            "  s.(name) = val;\n"
            "  r = s.(name);\n"
            "end\n"
        )
        f = import_matlab_func(code, is_code=True, scope=_STRUCT_SCOPE)
        assert f('b', 77) == 77
