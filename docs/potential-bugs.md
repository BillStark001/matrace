# Potential Bugs and Limitations

This document catalogs known issues, limitations, and potential bugs in the matrace codebase.

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

### 8. Linear Indexing Column-Major Conversion

**Location**: `matrace/stdlib/indexing.py`

**Issue**: MATLAB uses column-major linear indexing; conversion to row-major PyTorch may have edge cases.

**Complex Example**:
```matlab
A = [1 2 3; 4 5 6];
A([1 3 5])  % Linear indices: 1, 3, 5
% MATLAB result: [1 2 3] (column-major: A(1)=1, A(3)=2, A(5)=3)
```

**Testing Status**: Basic cases work; complex patterns untested

**Priority**: Medium - core feature

## String Handling

### 9. String Support Incomplete

**Location**: `matrace/interpreter/executor.py`

**Issue**: String handling is "basic" per code comments.

**Current Support**:
- ✅ String literals
- ✅ Char arrays
- ❓ String concatenation (unclear)
- ❌ String methods (e.g., `strfind`, `strcmp`)

**Example Unclear Behavior**:
```matlab
s1 = 'hello';
s2 = 'world';
s3 = [s1 ' ' s2];  % May or may not work
```

**Priority**: Low - numerical focus

### 10. String vs Char Array Confusion

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

### 12. Switch/Case Edge Cases

**Location**: `matrace/interpreter/cfg_executor.py`, `matrace/ir/cfg.py`

**Issue**: Switch statement implementation may have untested edge cases.

**Potential Issues**:
- Multiple case values: `case {1, 2, 3}`
- String cases
- Fall-through behavior

**Testing Status**: Basic cases tested; complex patterns unknown

**Priority**: Low - uncommon construct

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

### 17. Missing AST Node Handlers

**Location**: `matrace/interpreter/executor.py` and `matrace/interpreter/cfg_executor.py`

**Issue**: Many code paths have `assert False, 'TODO'` placeholders.

**Examples**:
- Unhandled literal types in `executor.py`
- Unhandled unary operators in `stdlib/operators.py`
- Unhandled binary operators in `stdlib/operators.py`

**Impact**: Unsupported MATLAB syntax causes runtime crashes instead of clear errors

**Priority**: Medium - affects robustness

## Operator Issues

### 18. Matrix Division Implementation

**Location**: `matrace/stdlib/operators.py`

**Issue**: Matrix division uses `torch.inverse()`, which:
- Fails for singular matrices
- Numerically unstable
- Slow for large matrices

**Better Alternative**: Use `torch.linalg.solve()` or `torch.linalg.lstsq()`

**Example Problem**:
```matlab
A = [1 2; 2 4];  % Singular matrix
B = [1; 2];
X = A \ B;       % Should use least-squares, not inverse
```

**Priority**: High - correctness and numerical stability

### 19. Matrix Power Integer Casting

**Location**: `matrace/stdlib/operators.py`

**Issue**: Matrix power assumes integer exponent:
```python
elem2_int = elem2[0][0]
```

**Potential Bug**: Fractional exponents may be truncated

**Example**:
```matlab
A = [4 0; 0 9];
B = A^0.5;  % Should give [[2 0]; [0 3]], may fail
```

**Priority**: Medium - fractional powers less common

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

### 22. Mixed Cell/Matrix Operations

**Location**: `matrace/stdlib/cells.py`, `matrace/stdlib/matrix.py`

**Issue**: Boundary between cell arrays and matrices may be unclear.

**Example**:
```matlab
C = {[1 2], [3 4]};
D = [C{:}];  % Cell expansion - may not work
```

**Priority**: Low - mixed usage uncommon

### 23. Nested Cell Indexing

**Issue**: Deeply nested cell arrays may have indexing issues.

**Example**:
```matlab
C = {{{1}}};
x = C{1}{1}{1};  % Triple nesting
```

**Testing Status**: Unknown

**Priority**: Low - deep nesting rare

## Struct Issues

### 24. Dynamic Field Names

**Location**: `matrace/interpreter/executor.py` (Dynamic_Selection handling)

**Issue**: Dynamic field access `s.(fieldname)` implementation unclear.

**Example**:
```matlab
field = 'myfield';
s.(field) = 42;  % Dynamic field access
```

**Testing Status**: Unknown

**Priority**: Low - less common pattern

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

### 29. Limited Test Coverage

**Current Tests**: Basic operations, simple control flow, ODE examples

**Missing Tests**:
- Edge cases for indexing
- Complex nested loops
- Exception handling
- String operations
- Cell array operations
- Struct arrays
- Large matrix performance

**Priority**: High - testing is critical

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

### High Priority
1. Copy-on-write not implemented
2. Matrix division numerical issues
3. Limited test coverage

### Medium Priority
4. N-dimensional array support
5. Function handle support missing
6. No static type checking
7. Linear indexing conversion edge cases
8. No expression memoization
9. Tensor cloning strategy unclear
10. Poor error messages
11. Missing AST node handlers
12. Matrix power integer casting

### Low Priority
- All others

## Recommendations

1. **Immediate**: Fix matrix division to use `torch.linalg.solve()`
2. **Short-term**: Implement copy-on-write semantics
3. **Medium-term**: Add comprehensive test suite
4. **Long-term**: Static type system and optimization passes

## Notes for Developers

When encountering `assert False, 'TODO'` in code:
1. Determine if feature is needed for your use case
2. If needed, implement with test case
3. If not needed, consider raising more descriptive error

When adding new features:
1. Add test cases first
2. Update this document with any limitations
3. Update `matlab-subset.md` with supported features
