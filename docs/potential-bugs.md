# Potential Bugs and Limitations

This document catalogs known issues, limitations, and potential bugs in the matrace codebase.

> **Change log** — items marked ✅ **Fixed** or 🎯 **By design** have been
> resolved in recent development.  See each entry for details.

## Critical Issues

### 1. Copy-on-Write Not Implemented

**Location**: `matrace/interpreter/executor.py`, `matrace/stdlib/indexing.py`

**Issue**: MATLAB uses copy-on-write semantics for efficiency, but matrace does not implement this optimization.

**Behavior**:
```matlab
A = [1 2; 3 4];
B = A;          % In MATLAB, B is a reference until modified
B(1,1) = 10;    % Now B is a copy
```

**Current Implementation**: May share references unintentionally or copy unnecessarily.

**Impact**: 
- Memory inefficiency
- Potential unexpected mutations
- Incorrect behavior when references should be copies

**Workaround**: Manually use `.clone()` when needed.

**Priority**: High - affects correctness

### 2. N-Dimensional Array Support Limited

**Location**: `matrace/stdlib/indexing.py`, `matrace/stdlib/matrix.py`

**Issue**: All matrices internally represented as 2D tensors.

**Behavior**: 
- 3D+ arrays may not work correctly
- Reshaping operations may fail
- Linear indexing assumes 2D column-major layout

**Example Failure**:
```matlab
A = rand(2, 3, 4);  % 3D array
A(1,2,3)            % May not work
```

**Impact**: Limits applicability to N-D computations (common in deep learning)

**Priority**: Medium - limits use cases

### 3. Function Handle Support Missing

**Location**: `matrace/interpreter/executor.py`

**Issue**: Anonymous functions and function handles not implemented.

**Behavior**:
```matlab
f = @(x) x^2;       % Not supported
y = f(5);           % Will fail
```

**Impact**: Cannot use functional programming patterns or callbacks

**Workaround**: Inject functions via `scope` parameter

**Priority**: Medium - common feature but workaround exists

## Type System Issues

### 4. No Static Type Checking

**Location**: All execution modules (`matrace/interpreter/`)

**Issue**: Types determined dynamically at runtime; no static analysis.

**Implications**:
- Type errors only detected during execution
- No IDE support for type hints
- Performance overhead from runtime type checks

**Impact**: 
- Debugging difficulty
- Runtime errors instead of compile-time errors

**Priority**: Medium - affects usability

### 5. Type Coercion Inconsistencies

**Location**: `matrace/interpreter/executor.py`, `matrace/stdlib/operators.py`

**Issue**: Type coercion rules may differ from MATLAB.

**Examples**:
- Scalar vs. matrix operations
- Integer vs. float promotion
- Logical vs. numeric conversion

**Potential Failures**:
```matlab
A = [1 2];
B = true;
C = A + B;  % Type coercion may differ from MATLAB
```

**Priority**: Low - rare in practice

## Indexing Issues

### 6. Complex Logical Indexing

**Location**: `matrace/stdlib/indexing.py`

**Issue**: Advanced logical indexing patterns may not work correctly.

**Example Problems**:
```matlab
A(A > 5 & A < 10) = 0;  % Complex logical condition
A([true false true]) = B;  % Logical index assignment
```

**Impact**: Limits advanced array manipulation

**Priority**: Low - basic indexing works

### 7. End Keyword Context Sensitivity

**Location**: `matrace/interpreter/executor.py` (MatrixContext)

**Issue**: `end` keyword relies on context manager stack; nested indexing may confuse it.

**Example Failure**:
```matlab
A(1:end, B(end))  % Nested 'end' may use wrong context
```

**Current Implementation**: Uses `mat_ctx` stack, but complex nesting untested

**Priority**: Low - uncommon case

### 8. Linear Indexing Column-Major Conversion ✅ Fixed

**Location**: `matrace/stdlib/indexing.py`

**Issue**: MATLAB uses column-major linear indexing; the documented expected
result was incorrect and test coverage was missing.

**Fix applied**:
- Corrected the example in this document (`[1 5 3]` → `[1 2 3]`).
- Added tests in `tests/test_slice.py` that lock in column-major linear
  indexing semantics for row vectors, column vectors, and subsets.

```matlab
A = [1 2 3; 4 5 6];
A([1 3 5])  % Linear indices: 1, 3, 5
% MATLAB result: [1 2 3] (column-major: A(1)=1, A(3)=2, A(5)=3)
```

**Testing Status**: Basic and subset cases covered by tests.

**Priority**: Medium - core feature

## String Handling

### 9. String Support ✅ Fixed (concatenation)

**Location**: `matrace/stdlib/matrix.py`

**Previous issue**: Horizontal char-array concatenation `[s1 ' ' s2]` was
not guaranteed to work.

**Fix applied** (`eval_row_cat`): When any item in a matrix row is a Python
`str`, all items are joined as strings before any tensor handling, making
`[s1 ' ' s2]` produce the expected concatenated string.

**Remaining limitation**: String *methods* (e.g. `strfind`, `strcmp`,
`strsplit`) are not implemented and must be injected via the `scope`
parameter.

**Current Support**:
- ✅ String literals (`"text"`)
- ✅ Char arrays (`'text'`)
- ✅ String concatenation (`[s1 ' ' s2]`)
- ❌ String methods — inject via `scope`

**Priority**: Low - numerical focus

### 10. String vs Char Array Confusion 🎯 By design

**Issue**: Implementation treats both `String_Literal` and `Char_Array_Literal` as Python strings.

**MATLAB Distinction**:
- `'text'` is char array
- `"text"` is string object (different type)

**Current Design Decision**: Both literal forms map to a plain Python `str`.
This is intentional for matrace's numerical focus — string-specific MATLAB
functions are not a priority.  The interpreter will not distinguish between
the two types.

**Known Impact**: String-specific MATLAB functions (e.g. `regexp`,
`strsplit`, `num2str`) are not implemented and will require injection via
the `scope` parameter.

**Priority**: Low — by design; no change planned

## Control Flow

### 11. SPMD Block Non-Functional

**Location**: `matrace/ir/cfg.py`

**Issue**: SPMD (Single Program Multiple Data) blocks parsed but not executed in parallel.

**Behavior**:
```matlab
spmd
    % This code runs serially, not in parallel
    A = rand(100);
end
```

**Impact**: No parallel computation support

**Priority**: Low - niche feature

### 12. Switch/Case ✅ Fixed

**Location**: `matrace/interpreter/cfg_executor.py`, `matrace/ir/cfg.py`

**Previous issues**:
- Switch statement entirely unhandled (`assert False`).
- No fallthrough when no case matched and no `otherwise` clause.

**Fixes applied**:
- `process_switch_statement` (`cfg.py`): adds an unconditional fallthrough
  edge to `end_switch` when no `otherwise` clause is present.
- `exec_node` (`cfg_executor.py`): `SWITCH_ENTRY` now evaluates and pushes
  the switch expression value onto a stack.
- `get_next_node` (`cfg_executor.py`): overridden for `SWITCH_ENTRY` to
  compare the stored value against each case expression using
  `_switch_match`, which handles numeric equality, string equality, and
  cell-set membership (`case {1, 2, 3}`).
- `SWITCH_ACTION_ENTRY`, `SWITCH_EXIT` added to `NO_OPR_TYPES`.

**Testing**: covered by `tests/test_strings_cells.py::TestSwitchStatement`.

**Priority**: ✅ resolved

## Memory and Performance

### 13. No Expression Memoization

**Issue**: Repeated expression evaluation has no caching.

**Example**:
```matlab
for i = 1:1000
    y = expensive_function(x);  % Re-evaluated every iteration
end
```

**Impact**: Performance overhead for repeated operations

**Priority**: Medium - affects performance

### 14. Variable Scope Memory Leaks

**Location**: `matrace/interpreter/executor.py` (vars dictionary)

**Issue**: Variables not cleaned up after function execution.

**Behavior**: Each function call accumulates variables in memory

**Potential Memory Leak**: Long-running programs may accumulate state

**Priority**: Low - typically short-lived executions

### 15. Tensor Cloning Overhead

**Location**: `matrace/stdlib/indexing.py`

**Issue**: `copy_required` flag triggers tensor cloning, but unclear when this is needed.

**Current Implementation**:
```python
if copy_required:
    node = node.clone()
```

**Problem**: Conservative cloning may waste memory; insufficient cloning may cause bugs

**Priority**: Medium - correctness vs. performance tradeoff

## Parser and AST Issues

### 16. Error Messages Poor Quality

**Location**: `matrace/parser/parser.py` (ModifiedMessageHandler)

**Issue**: Parser errors not user-friendly.

**Current Behavior**: Throws generic exception with location
```python
raise Exception(msg.location, msg.message)
```

**Impact**: Debugging MATLAB syntax errors is difficult

**Priority**: Medium - usability issue

### 17. Missing AST Node Handlers ✅ Fixed

**Location**: `matrace/interpreter/executor.py`, `matrace/interpreter/cfg_executor.py`, `matrace/stdlib/operators.py`

**Previous issue**: Many code paths had bare `assert False, 'TODO'`
placeholders that:
- Could be silently disabled with Python's `-O` flag.
- Produced unhelpful `AssertionError` instead of a clear error type.

**Fixes applied** — all `assert False` replaced with proper exceptions:

| Location | Old | New |
|---|---|---|
| `stdlib/operators.py` — `eval_unary_opr` fallthrough | `assert False, 'TODO'` | `NotImplementedError` |
| `stdlib/operators.py` — `eval_binary_opr` fallthrough | `assert False, 'TODO'` | `NotImplementedError` |
| `stdlib/operators.py` — `mpower` scalar check | `assert elem2.numel() == 1` | `ValueError` |
| `stdlib/indexing.py` — `parse_subsref_arr_slice` fallthrough | `assert False, 'TODO'` | `NotImplementedError` |
| `stdlib/indexing.py` — `gen_torch_slice_by_subsref_slice` >2 subs | `assert False, 'TODO'` | `NotImplementedError` |
| `stdlib/indexing.py` — empty-subs invariant | `assert assign_rhs is None, 'WTF'` | `ValueError` |
| `stdlib/cells.py` — `concat_cells_row` row-count mismatch | `assert row_number == item_row_number` | `ValueError` |
| `stdlib/structs.py` — `create_struct` key-type check | `assert isinstance(args[i], str)` | `TypeError` |
| `interpreter/executor.py` — `eval` type guard | `assert isinstance(node, Expression)` | `TypeError` |
| `interpreter/executor.py` — `subsasgn` LHS fallthrough | `assert False, 'WTF'` | `ValueError` |
| `interpreter/executor.py` — `eval` expression fallthrough | `assert False, 'TODO: ...'` | `NotImplementedError` |
| `interpreter/executor.py` — `expr_literal` fallthrough | `assert False, 'TODO'` | `NotImplementedError` |
| `interpreter/cfg_executor.py` — unhandled CFG node | `assert False, 'TODO'` | `NotImplementedError` |
| `interpreter/cfg_executor.py` — CFG dead-end | `assert False, 'Should not happen'` | `RuntimeError` |
| `interpreter/cfg_executor.py` — unknown string sentinel | `assert False, 'TODO'` | `NotImplementedError` |
| `api/import_func.py` — function not found | `assert func_ast is not None` | `ValueError` |
| `parser/parser.py` — message type guard | `assert isinstance(msg, Message)` | `TypeError` |
| `analysis/type_parser.py` — brace precondition | `assert s[start] == "{"` | `ValueError` |

**Priority**: ✅ resolved

## Operator Issues

### 18. Matrix Division Implementation ✅ Fixed

**Location**: `matrace/stdlib/operators.py`

**Previous issue**: Matrix division used `torch.inverse()`, which fails for
singular matrices and is numerically unstable.

**Fix applied**: Both `mrdivide` (`/`) and `mldivide` (`\`) now use
`torch.linalg.solve()`:

```python
# mrdivide: X * B = A  →  B^T * X^T = A^T  →  X = solve(B^T, A^T)^T
return torch.linalg.solve(elem2.mT, elem1.mT).mT

# mldivide: A * X = B  →  X = solve(A, B)
return torch.linalg.solve(elem1, elem2)
```

**Testing**: covered by `tests/test_math.py::test_mldivide_*` and `test_mrdivide_*`.

**Priority**: ✅ resolved

### 19. Matrix Power Integer Casting ✅ Fixed

**Location**: `matrace/stdlib/operators.py`

**Previous issue**: `elem2[0][0]` returned a 0-d tensor incompatible with
`torch.linalg.matrix_power`; fractional exponents were silently truncated.

**Fix applied**:
- `elem2.item()` used to extract a Python scalar.
- Non-integer matrix exponents now raise `NotImplementedError` with a
  descriptive message suggesting `.^` for element-wise exponentiation.
- Scalar `^` fractional exponents continue to work.

**Testing**: covered by `tests/test_math.py::test_matrix_power_*`.

**Priority**: ✅ resolved

## Function Call Issues

### 20. Variable Number of Outputs Not Fully Supported

**Location**: `matrace/api/import_func.py`, `matrace/interpreter/cfg_executor.py`

**Issue**: MATLAB functions can have variable number of output arguments; not fully handled.

**Example**:
```matlab
function [a, b, c] = multi_out(x)
    a = x;
    b = x^2;
    c = x^3;
end

y = multi_out(5);        % Returns [a, b, c] or just a?
[p, q] = multi_out(5);   % How to handle?
```

**Current Behavior**: Returns all outputs as tuple/list

**Priority**: Low - usually straightforward

### 21. Nargin/Nargout Not Implemented

**Issue**: MATLAB's `nargin` and `nargout` keywords not supported.

**Example**:
```matlab
function y = flexible(x, opt)
    if nargin < 2
        opt = 'default';
    end
    % ...
end
```

**Impact**: Cannot write functions with optional arguments

**Workaround**: Python default parameters in injected functions

**Priority**: Low - workaround available

## Cell Array Issues

### 22. Mixed Cell/Matrix Operations ✅ Fixed

**Location**: `matrace/stdlib/cells.py`, `matrace/stdlib/matrix.py`

**Previous issue**: `[C{:}]` cell expansion into a matrix did not work.

**Fix applied**:
- `CellExpansion` class added to `cells.py`; `eval_subsref_cell` returns a
  `CellExpansion` when indexed with `{:}` (colon), containing all elements
  in column-major order.
- `eval_row_cat` in `matrix.py` expands `CellExpansion` objects before
  other processing, so `[E{:}]` correctly concatenates all cell elements.

**Example (now working)**:
```matlab
C = {[1 2], [3 4]};
D = [C{:}];  % → [[1 2 3 4]]
```

**Testing**: covered by `tests/test_strings_cells.py::TestCellExpansion`.

**Priority**: ✅ resolved

### 23. Nested Cell Indexing ✅ Fixed

**Location**: `matrace/stdlib/cells.py`, `matrace/interpreter/executor.py`

**Previous issue**: Cell indexing used `obj[*target]` which failed for
anything but trivially-shaped lists.

**Fix applied**:
- `eval_subsref_cell` in `cells.py`: correct 1-based, column-major linear
  indexing; two-subscript `{i, j}` access; colon `{:}` expansion.
- `subsasgn_cell` in `cells.py`: in-place cell element assignment.
- `eval_col_cat` in `matrix.py`: cell-expression path simplified —
  builds `List[List[Any]]` directly from evaluated rows, fixing a
  flat-vs-nested inconsistency that broke single-row cells.
- `executor.py`: uses `eval_subsref_cell` / `subsasgn_cell` instead of the
  broken `subsref_list` / direct list-index hack.

**Example (now working)**:
```matlab
C = {{{99}}};
x = C{1}{1}{1};  % → 99
```

**Testing**: covered by `tests/test_strings_cells.py::TestNestedCellIndexing`.

**Priority**: ✅ resolved

## Struct Issues

### 24. Dynamic Field Names ✅ Verified working

**Location**: `matrace/interpreter/executor.py` (Dynamic_Selection handling)

**Previous status**: Untested.

**Current status**: The existing `Dynamic_Selection` read/write paths
(`getattr`/`setattr` on `DictWrapper`) work correctly for both reading and
writing.

**Example (working)**:
```matlab
field = 'myfield';
s.myfield = 0;
s.(field) = 42;   % Dynamic field write
v = s.(field);    % Dynamic field read  → 42
```

**Testing**: covered by `tests/test_strings_cells.py::TestDynamicFieldAccess`.

**Priority**: ✅ resolved

### 25. Struct Arrays — Intentionally Unsupported

**Issue**: Arrays of structures (`s(1).field`, `s(2).field`) are not
supported.

**Example (unsupported)**:
```matlab
s(1).field = 1;
s(2).field = 2;
values = [s.field];  % Array expansion
```

**Design Decision**: Struct *scalars* (single `DictWrapper` objects) are
supported.  Struct *arrays* require combining tensor indexing with struct
field access, which conflicts with the current `DictWrapper` implementation
and is out of scope for matrace's numerical focus.

**Workaround**: Use cell arrays of structs, or pre-allocate individual
named variables.

**Priority**: Out of scope — not planned

## General Limitations

### 26. No Debugger Support

**Issue**: No step-through debugging of MATLAB code execution.

**Impact**: Debugging requires print statements or Python debugger on executor

**Priority**: Medium - development experience

### 27. No Profiling Support

**Issue**: Cannot profile MATLAB code performance.

**Impact**: Cannot identify bottlenecks in MATLAB code

**Priority**: Low - use PyTorch profiler instead

### 28. Limited Error Recovery

**Issue**: Errors in MATLAB code often crash entire execution.

**Better Behavior**: Graceful error messages with MATLAB line numbers

**Priority**: Medium - usability

## Testing Gaps

### 29. Test Coverage

**Current Tests**: Basic operations, simple control flow, ODE examples,
matrix division/power, linear indexing (column-major), string concatenation,
cell indexing (simple, nested, expansion), switch statement, dynamic struct
fields.

**Still missing**:
- Edge cases for logical indexing
- Complex nested loops (`continue` inside `for`)
- Exception handling (`try/catch`)
- String methods (injected via scope)
- Large matrix performance

**Priority**: Medium

### 30. No Integration Tests

**Issue**: No end-to-end tests of realistic MATLAB programs.

**Impact**: Unknown behavior on real-world code

**Priority**: Medium - needed for production use

## Documentation Issues

### 31. Minimal Inline Documentation

**Issue**: Many functions lack docstrings or comments.

**Impact**: Code maintenance difficulty

**Priority**: Low - this document addresses it

### 32. No User Examples

**Issue**: No documentation for end users on how to use the library.

**Impact**: Adoption barrier

**Priority**: Medium - addressed by new documentation

## Summary by Priority

### ✅ Resolved
- #8  Linear indexing documentation and tests
- #9  String concatenation
- #12 Switch/case statement (numeric, string, cell-set, otherwise, fallthrough)
- #17 All `assert False` / bare assertions replaced with proper exceptions
- #18 Matrix division numerical stability (`torch.linalg.solve`)
- #19 Matrix power integer casting (`.item()`, fractional exponent error)
- #22 Cell expansion `[C{:}]`
- #23 Nested cell indexing
- #24 Dynamic struct field access verified

### 🎯 By Design
- #10 Char-array vs string literal — both map to Python `str`
- #25 Struct arrays — intentionally unsupported

### High Priority (open)
1. Copy-on-write not implemented (#1)

### Medium Priority (open)
2. N-dimensional array support (#2)
3. Function handle support missing (#3)
4. No static type checking (#4)
5. No expression memoization (#13)
6. Tensor cloning strategy unclear (#15)
7. Poor parser error messages (#16)
8. No integration tests (#30)

### Low Priority
- All others

## Recommendations

1. **Next**: Implement copy-on-write semantics (#1) for correctness
2. **Short-term**: Improve parser error messages (#16)
3. **Medium-term**: Add integration tests (#30)
4. **Long-term**: Static type system and optimization passes

## Notes for Developers

All `assert False, 'TODO'` and bare `assert condition` have been replaced
with proper Python exceptions.  The conventions are:

| Situation | Exception to raise |
|---|---|
| Unhandled MATLAB syntax / operator | `NotImplementedError` |
| Unhandled internal code path (programming error) | `RuntimeError` |
| Wrong argument type passed to a function | `TypeError` |
| Wrong argument value (e.g. wrong shape) | `ValueError` |
| CFG execution reaches a dead end | `RuntimeError` |
| Function name not found in AST | `ValueError` |

When adding new features:
1. Add test cases first
2. Update this document with any limitations
3. Update `matlab-subset.md` with supported features
4. Use the exception conventions above; never use bare `assert`

