# MATLAB Subset Definition

Matrace supports a numerical computing-oriented subset of MATLAB, designed to enable compilation into PyTorch computational graphs. This document defines the supported language features.

## Supported Data Types

### 1. Numerical and Logical Matrices

All numerical/logical matrices are represented as 2D PyTorch tensors internally. The following categories are supported:

#### Matrix Categories
- **Scalar**: Single value (internally represented as 1×1 tensor)
- **Row Vector**: 1×N tensor
- **Column Vector**: N×1 tensor  
- **Matrix**: M×N tensor (M > 1, N > 1)

#### Length Constraints
Each category can be:
- **Fixed-length**: Size determined statically
- **Variable-length**: Size determined dynamically at runtime

#### Supported Element Types
- **Numerical**: Integer and floating-point values (stored as float tensors)
- **Logical**: Boolean values (stored as boolean tensors)

**Important**: Non-numerical and non-logical matrices are **not supported**. Use cell arrays for heterogeneous data.

### 2. Cell Arrays

Cell arrays store heterogeneous data of arbitrary types.

**Implementation**: Python lists (list of lists for 2D cells)
```matlab
C = {1, 'text', [1 2; 3 4]};  % 1×3 cell array
```

**Operations Supported**:
- Cell concatenation (horizontal `[C1, C2]` and vertical `[C1; C2]`)
- Cell indexing with `{}` notation: `C{1,2}`
- Mixed content (numbers, strings, matrices, nested cells)

### 3. Strings

String support includes character arrays, though implementation may have limitations.

**Supported**:
- `char` arrays: `'hello world'`
- String literals in expressions

**Note**: String handling is basic; advanced string operations may not be fully implemented. Verify specific use cases.

### 4. Structures (struct)

Structures group related data using named fields.

**Implementation**: `DictWrapper` (Python dictionary wrapper)
```matlab
s = struct('name', 'value', 'count', 42);
x = s.name;
```

**Operations Supported**:
- Field access with dot notation: `s.field`
- Dynamic field creation
- Structure arrays

### 5. Classes

**Status**: **Not Supported**

Classes, including:
- Class definitions
- Methods
- Inheritance
- Operator overloading
- Advanced OOP features

**Rationale**: Focus remains on numerical computing. OOP features are planned but not currently supported.

### 6. Functions and Function Handles

**Status**: **Partially Supported**

**Function Definitions**: 
- ✅ Supported: Regular function definitions with parameters and return values
- ✅ Supported: Multiple input/output arguments
- ✅ Supported: Nested functions (limited)

**Function Handles**: 
- ❌ Not Supported: Anonymous functions `@(x) x^2`
- ❌ Not Supported: Function handle assignment
- **Workaround**: Inject Python functions manually via the `scope` parameter

```python
# Manual function injection example
func = import_matlab_func(
    'my_script.m',
    scope={
        'sum': lambda x: torch.sum(x).unsqueeze(0).unsqueeze(0),
        'sqrt': lambda x: torch.sqrt(x)
    }
)
```

## Supported Operators

### Arithmetic Operators

| Operator | Name | Description |
|----------|------|-------------|
| `+` | plus | Element-wise or matrix addition |
| `-` | minus | Element-wise or matrix subtraction |
| `.*` | times | Element-wise multiplication |
| `*` | mtimes | Matrix multiplication |
| `./` | rdivide | Element-wise right division |
| `.^` | power | Element-wise exponentiation |
| `^` | mpower | Matrix power |
| `.\` | ldivide | Element-wise left division |
| `/` | mrdivide | Matrix right division (with inverse) |
| `\` | mldivide | Matrix left division (with inverse) |

### Logical Operators

| Operator | Name | Description |
|----------|------|-------------|
| `&` | and | Element-wise logical AND |
| `&&` | and | Short-circuit logical AND |
| `\|` | or | Element-wise logical OR |
| `\|\|` | or | Short-circuit logical OR |
| `~` | not | Logical NOT |
| `!` | not | Logical NOT (alternative) |

### Comparison Operators

| Operator | Name | Description |
|----------|------|-------------|
| `<` | lt | Less than |
| `>` | gt | Greater than |
| `<=` | le | Less than or equal |
| `>=` | ge | Greater than or equal |
| `==` | eq | Equal to |
| `~=` | ne | Not equal to |

### Unary Operators

| Operator | Name | Description |
|----------|------|-------------|
| `'` | ctranspose | Complex conjugate transpose |
| `.'` | transpose | Transpose |
| `+` | uplus | Unary plus |
| `-` | uminus | Unary minus |

## Supported Control Flow

### 1. Conditional Statements

#### if/elseif/else
```matlab
if condition1
    % code
elseif condition2
    % code
else
    % code
end
```

#### switch/case
```matlab
switch variable
    case value1
        % code
    case value2
        % code
    otherwise
        % code
end
```

### 2. Loops

#### for Loop
```matlab
for i = 1:10
    % code
end

for element = array
    % code
end
```

#### while Loop
```matlab
while condition
    % code
end
```

### 3. Loop Control

- `break`: Exit loop prematurely
- `continue`: Skip to next iteration

### 4. Exception Handling

```matlab
try
    % code that might error
catch
    % error handling
end
```

### 5. SPMD Blocks

**Status**: Parsed but minimal support
```matlab
spmd
    % parallel code
end
```

**Note**: SPMD (Single Program Multiple Data) blocks are recognized but parallel execution is not implemented.

## Indexing and Subscripting

### Array Indexing

**MATLAB uses 1-based indexing**; matrace automatically converts to 0-based for PyTorch.

#### Basic Indexing
```matlab
A(i, j)        % Element at row i, column j (1-based)
A(i)           % Linear indexing (column-major)
A(:, j)        % All rows, column j
A(i, :)        % Row i, all columns
```

#### Colon Operator
```matlab
A(1:5, :)      % Rows 1-5, all columns
A(2:2:10, 3)   % Rows 2,4,6,8,10, column 3
```

#### Logical Indexing
```matlab
A(A > 0)       % Elements greater than 0
```

#### end Keyword
```matlab
A(end, :)      % Last row
A(1:end-1, 2)  % All but last row, column 2
```

**Implementation Note**: The `end` keyword is context-aware and uses `MatrixContext` to determine array dimensions.

### Cell Indexing

```matlab
C{i, j}        % Access cell contents
C(i, j)        % Access cell container (returns cell)
```

### Structure Field Access

```matlab
s.fieldname         % Static field access
s.(dynamicField)    % Dynamic field access
```

## Special Features

### Matrix Construction

#### Concatenation
```matlab
[A, B]         % Horizontal concatenation
[A; B]         % Vertical concatenation
```

#### Inline Arrays
```matlab
A = [1 2 3]           % Row vector
B = [1; 2; 3]         % Column vector
C = [1 2; 3 4]        % 2×2 matrix
```

### Colon Operator for Ranges

```matlab
1:10           % 1 to 10 with step 1
1:2:10         % 1 to 10 with step 2
```

**Implementation**: Returns Python `slice` object or torch tensor depending on context.

## Limitations and Known Issues

### 1. Type System
- No static type checking
- Dynamic type inference at runtime
- All matrices are internally 2D tensors (may cause issues with N-D arrays)

### 2. String Handling
- Basic string support only
- String concatenation may be limited
- Character array manipulation is basic

### 3. Function Features
- No anonymous functions (`@(x) x^2`)
- No function handles as first-class values
- Limited closure support
- External functions must be manually injected

### 4. Advanced Indexing
- Multi-dimensional arrays (N > 2) not fully supported
- Some advanced indexing patterns may fail

### 5. OOP Features
- No class definitions
- No methods or inheritance
- No operator overloading for custom types

### 6. Parallel Computing
- SPMD blocks recognized but not executed in parallel
- No `parfor` support

### 7. Copy Semantics
- No copy-on-write optimization
- All assignments create references (may need explicit `.clone()`)
- Potential memory inefficiency for large matrices

## Recommendations for Users

1. **Keep code simple**: Stick to numerical operations and basic control flow
2. **Avoid advanced features**: Classes, function handles, and advanced indexing may not work
3. **Test incrementally**: Verify each function works before combining
4. **Inject external functions**: Use `scope` parameter for library functions
5. **Use explicit types**: Although dynamic, document expected types in comments
6. **Watch for mutations**: Be aware that matrix operations may modify in-place

## Future Enhancements

See `roadmap.md` for planned improvements including:
- Static type annotations (JSDoc-style)
- Copy-on-write analysis
- Static compilation support
- Enhanced class support
