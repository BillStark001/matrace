# Architecture Documentation

This document describes the internal architecture and module organization of matrace.

## Overview

Matrace transforms MATLAB code into PyTorch-executable Python functions through a multi-stage pipeline:

```
MATLAB Source → Parsing → AST → CFG → Execution → PyTorch Operations
```

The architecture is organized into 4 main layers:

1. **Parsing Layer** (`helper.py`) - MATLAB code parsing
2. **AST/CFG Layer** (`mh/`) - Abstract syntax tree and control flow graph generation
3. **Execution Layer** (`exec_*.py`) - Code interpretation and execution
4. **Standard Library** (`std/`) - PyTorch-based MATLAB operation implementations

## Module Structure

### Root Directory

```
matrace/
├── helper.py          # Entry point for importing MATLAB functions
├── exec_flow.py       # Expression evaluator
├── exec_cfg.py        # Control flow executor
├── mh/                # MATLAB AST and CFG handling
│   ├── ast.py         # AST visitor pattern
│   └── cfg.py         # Control flow graph generation
├── std/               # Standard library operations
│   ├── opr.py         # Basic operators
│   ├── mat_opr.py     # Matrix operations
│   ├── mat_subs.py    # Subscripting and indexing
│   ├── cell_opr.py    # Cell array operations
│   └── struct.py      # Structure operations
└── utils/             # Utility modules
    ├── context.py     # Context managers
    ├── nested_dict.py # Nested dictionary helpers
    ├── dict_wrapper.py # Dictionary wrapper for structs
    └── ...
```

## Core Modules

### 1. helper.py - Entry Point

**Purpose**: Main API for importing and executing MATLAB functions.

**Key Functions**:
- `parse_matlab_code(content, path)`: Parse MATLAB source into AST
- `import_matlab_func(path_or_code, scope, function_name, is_code, return_ast)`: Import MATLAB functions as Python callables

**Workflow**:
1. Read MATLAB file or code string
2. Lexical analysis using `MATLAB_Lexer`
3. Parse into AST using `MATLAB_Parser`
4. Extract function definitions by name
5. Wrap in Python callable with scope injection

**Dependencies**: `miss_hit_core` library for MATLAB parsing

**Example Usage**:
```python
func = import_matlab_func(
    'my_script.m',
    scope={'sqrt': torch.sqrt},
    function_name='main'
)
result = func(arg1, arg2)
```

### 2. mh/ast.py - AST Visitor

**Purpose**: Generic visitor pattern for traversing MATLAB abstract syntax trees.

**Key Class**: `MatlabAstVisitor`
- Implements visitor pattern for all AST node types
- Extensible base class for custom AST processors

**Usage**: Extend this class to implement custom AST transformations or analysis.

### 3. mh/cfg.py - Control Flow Graph

**Purpose**: Convert MATLAB statements into a control flow graph for execution.

**Key Components**:

#### CFGType Enumeration
Defines node types in the control flow graph:
- `SEQUENCE`: Linear statement sequence
- `GLOBAL_ENTRY/EXIT`: Function entry/exit points
- `IF_ENTRY/EXIT/ACTION_ENTRY`: Conditional branches
- `FOR_ENTRY/EXIT/INIT/CONTINUE`: For loop structure
- `WHILE_ENTRY/EXIT/CONTINUE`: While loop structure
- `SWITCH_ENTRY/EXIT/ACTION_ENTRY`: Switch statements
- `TRY_ENTRY/EXIT/CATCH`: Exception handling
- `SPMD_ENTRY/EXIT`: Parallel blocks
- `BREAK/CONTINUE/RETURN`: Control flow breaks

#### CFGNode
Represents a node in the control flow graph:
```python
@dataclass
class CFGNode:
    uid: int                              # Unique identifier
    type: int                             # CFGType value
    label: str                            # Human-readable label
    stmt_list: Optional[Sequence_Of_Statements]  # Statements to execute
```

#### CFGEdge
Represents edges between nodes:
```python
@dataclass
class CFGEdge:
    from_node: int                        # Source node ID
    to_node: int                          # Target node ID
    label: str                            # Edge description
    cond: Optional[Expression]            # Condition for edge traversal
    precedence: Optional[int]             # Edge priority
```

#### CFG Class
Main control flow graph structure:
- `nodes`: Dictionary of all CFG nodes
- `edges`: Dictionary mapping node IDs to outgoing edges
- `entry_id/exit_id`: Entry and exit node IDs
- `add_node()`: Create new CFG node
- `add_edge()`: Create edge between nodes

**Key Function**: `generate_cfg(stmts)` - Convert statement list to CFG

**Workflow**:
1. Create entry and exit nodes
2. Recursively process each statement type
3. Build edges representing control flow
4. Handle loops, conditionals, and exceptions

### 4. exec_flow.py - Expression Evaluator

**Purpose**: Evaluate MATLAB expressions and execute simple statements.

**Key Class**: `CodeExecutor`

**Attributes**:
- `vars`: Dictionary storing variable bindings
- `mat_ctx`: Context manager for matrix shape tracking (for `end` keyword)

**Core Methods**:

#### `eval(node)` - Expression Evaluation
Recursively evaluates expressions using visitor pattern:
- Literals: `Number_Literal`, `String_Literal`, `Char_Array_Literal`
- Identifiers: Variable lookups
- Binary operations: `+`, `-`, `*`, etc.
- Unary operations: `-`, `~`, `'`
- Array construction: `[...]` syntax
- Function calls: Execute injected functions
- Subscripting: Array and cell indexing

#### `subsasgn(node)` - Assignment
Handles variable assignments:
- Simple: `x = expr`
- Compound: `x += expr` (though limited support)
- Subscripted: `A(i,j) = expr`
- Field: `s.field = expr`

#### `exec(node)` - Statement Execution
Execute sequences of simple statements.

**Special Features**:
- **MatrixContext**: Tracks current array dimensions for `end` keyword resolution
- **Colon operator**: Generates `slice` objects for ranges
- **1-based indexing**: Transparent conversion to 0-based PyTorch indexing

### 5. exec_cfg.py - Control Flow Executor

**Purpose**: Execute control flow graphs with loop and branching support.

**Key Class**: `CodeControlExecutor` (extends `CodeExecutor`)

**Additional Attributes**:
- `for_loop`: Context manager stack for nested loops

**Key Method**: `exec_node(node)`
Executes individual CFG nodes based on type:

#### Loop Execution
**FOR_INIT**: 
- Evaluate loop range/array
- Create generator for iteration
- Push `ForLoopContext` onto stack

**FOR_ENTRY**:
- Get next element from generator
- Bind to loop variable
- Set `has_next` flag

**FOR_EXIT**:
- Pop loop context from stack

#### Conditional Execution
**IF/SWITCH evaluation**: Evaluate conditions and follow appropriate edge

#### Exception Handling
**TRY/CATCH blocks**: Execute try block and catch exceptions

**Workflow**:
1. Start at entry node
2. Execute node based on type
3. Evaluate edge conditions
4. Follow edges to next node
5. Repeat until exit node reached

### 6. std/opr.py - Basic Operators

**Purpose**: Implement MATLAB operators using PyTorch operations.

**Key Functions**:

#### `eval_unary_opr(opr, elem)`
Unary operations:
- `'` (ctranspose): Conjugate transpose
- `.'` (transpose): Real transpose
- `-` (uminus): Negation
- `~` (not): Logical NOT

#### `eval_binary_opr(opr, elem1, elem2)`
Binary operations:
- Arithmetic: `+`, `-`, `.*`, `*`, `./`, `/`, `.^`, `^`
- Comparison: `<`, `>`, `<=`, `>=`, `==`, `~=`
- Logical: `&`, `|`, `&&`, `||`

**Implementation Notes**:
- Matrix division uses `torch.inverse()`
- Matrix power uses `torch.linalg.matrix_power()`
- Element-wise operations broadcast naturally
- Logical operations use `torch.logical_*` functions

### 7. std/mat_opr.py - Matrix Operations

**Purpose**: Matrix construction and manipulation.

**Key Functions**:
- `eval_col_cat(items)`: Vertical concatenation `[A; B]`
- `eval_row_cat(items)`: Horizontal concatenation `[A, B]`
- Matrix reshaping and size operations

### 8. std/mat_subs.py - Subscripting

**Purpose**: Handle MATLAB array subscripting with 1-based indexing.

**Key Functions**:

#### `parse_subsref_arr_slice(sub, is_mono)`
Convert MATLAB subscript to PyTorch indexing:
- Slice objects: `a:b:c` → Python slice (adjusted for 0-based)
- Integers: Single indices (subtract 1)
- Tensors: Index arrays (subtract 1, flatten if needed)

#### `gen_torch_slice_by_subsref_slice(subs_parsed, size)`
Generate 2D index tensors for subscripting:
- Linear indexing: Convert to row/col indices
- 2D indexing: Create meshgrid
- Proper shape handling for row/column vectors

#### `commit_subsref_or_subsasgn_arr(node, subs_parsed, assign_rhs, copy_required)`
Execute actual subscripting operation:
- **Subscripting**: `A(indices)` returns selected elements
- **Assignment**: `A(indices) = value` updates elements
- **Copy handling**: Optional cloning for copy-on-write

**Complexity**: Linear indexing in MATLAB is column-major; requires careful conversion.

### 9. std/cell_opr.py - Cell Operations

**Purpose**: Cell array manipulation.

**Key Functions**:
- `concat_cells_row(items)`: Horizontal cell concatenation
- `concat_cells_col(items)`: Vertical cell concatenation

**Implementation**: Cells are Python lists; operations preserve 2D structure.

### 10. std/struct.py - Structures

**Purpose**: MATLAB struct implementation.

**Key Function**:
- `create_struct(*args, **kwargs)`: Create structure from key-value pairs

**Implementation**: Uses `DictWrapper` to provide both dictionary and attribute access.

### 11. utils/context.py - Context Management

**Purpose**: Stack-based context management for nested scopes.

**Key Class**: `ContextManager`
- Push/pop context values
- Access current context
- Used for loop variables and matrix dimensions

### 12. utils/dict_wrapper.py - Dictionary Wrapper

**Purpose**: Provide attribute-style access to dictionaries (for structs).

**Key Class**: `DictWrapper`
```python
s = DictWrapper({'field': 42})
x = s.field  # Attribute access
x = s['field']  # Dictionary access
```

## Execution Flow

### Complete Pipeline

1. **Parse MATLAB Code** (`helper.py`):
   ```
   MATLAB source → MATLAB_Lexer → MATLAB_Parser → AST
   ```

2. **Extract Function** (`helper.py`):
   ```
   AST → find function by name → Function_Definition
   ```

3. **Generate CFG** (`mh/cfg.py`):
   ```
   Function_Definition → generate_cfg() → CFG
   ```

4. **Execute Function** (`exec_cfg.py`):
   ```
   CFG + args → CodeControlExecutor → traverse nodes → result
   ```

5. **Evaluate Expressions** (`exec_flow.py`):
   ```
   Expression → CodeExecutor.eval() → PyTorch operations
   ```

### Example: Simple Function

MATLAB code:
```matlab
function y = square(x)
    y = x * x;
end
```

Execution trace:
1. Parse: Create AST with function definition
2. Import: Wrap function in Python callable
3. Call: `result = square(torch.tensor([[3.0]]))`
4. CFG: Entry → Assignment → Exit
5. Eval: 
   - Evaluate `x * x`
   - Lookup `x` in vars
   - Call `eval_binary_opr('*', x, x)`
   - Return PyTorch tensor result
6. Assign to `y`
7. Return `y`

## Design Patterns

### 1. Visitor Pattern
Used in `mh/ast.py` for extensible AST traversal.

### 2. Context Management
`ContextManager` provides clean stack-based scope management.

### 3. Factory Pattern
CFG nodes and edges created through factory methods in `CFG` class.

### 4. Strategy Pattern
Different node types execute different strategies in `exec_node()`.

## Thread Safety

**Current Status**: Not thread-safe

**Issues**:
- Global variable dictionary modifications
- Context manager state
- No locking mechanisms

**Recommendation**: Use separate executor instances for concurrent execution.

## Performance Considerations

### Bottlenecks
1. **Dynamic interpretation**: Every expression evaluated at runtime
2. **Type checking**: Runtime type inference overhead
3. **No caching**: Repeated code paths re-evaluated

### Optimization Opportunities
1. **Static compilation**: Pre-compute types when possible
2. **JIT compilation**: Use `torch.jit.trace()` for traced execution
3. **Expression caching**: Memoize common expression patterns
4. **Type hints**: User-provided type annotations could enable optimization

## Extension Points

### Adding New Operators
1. Add case in `eval_binary_opr()` or `eval_unary_opr()`
2. Implement using PyTorch operations
3. Test with MATLAB examples

### Adding New Statement Types
1. Add CFGType enumeration
2. Implement CFG generation in `cfg.py`
3. Add execution case in `exec_node()`
4. Test with control flow examples

### Adding Built-in Functions
Inject via `scope` parameter:
```python
import_matlab_func(
    'script.m',
    scope={
        'sin': torch.sin,
        'cos': torch.cos,
        'sum': lambda x: torch.sum(x, dim=0, keepdim=True)
    }
)
```

## Related Documentation

- `matlab-subset.md`: Supported MATLAB features
- `potential-bugs.md`: Known issues and limitations
- `roadmap.md`: Future development plans
