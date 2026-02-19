# Architecture Documentation

This document describes the internal architecture and module organization of matrace.

## Overview

Matrace transforms MATLAB code into PyTorch-executable Python functions through a multi-stage pipeline:

```
MATLAB Source → Parsing → AST → CFG → Execution → PyTorch Operations
```

The architecture is organized into 6 main layers:

1. **Public API** (`api/`) – stable entry point
2. **Parsing Layer** (`parser/`) – MATLAB source → AST
3. **IR / CFG Layer** (`ir/`) – control flow graph and AST utilities
4. **Interpreter** (`interpreter/`) – dynamic code execution
5. **Standard Library** (`stdlib/`) – PyTorch implementations of MATLAB operations
6. **Type System** (`types/`) + **Analysis** (`analysis/`) – type hierarchy and JSDoc annotation parser

## Module Structure

```
matrace/
├── __init__.py            # Lazy re-exports (import_matlab_func, type classes, …)
├── api/
│   └── import_func.py     # Public entry point: import_matlab_func()
├── parser/
│   ├── parser.py          # MATLAB lexer/parser wrapper (miss_hit_core)
│   └── ast_utils.py       # get_function_by_name() helper
├── ir/
│   ├── cfg.py             # Control flow graph (CFG, CFGNode, CFGEdge, generate_cfg)
│   └── ast_visitor.py     # Generic MATLAB AST visitor base class
├── interpreter/
│   ├── executor.py        # Expression evaluator (CodeExecutor)
│   └── cfg_executor.py    # CFG-based control flow executor (exec_func)
├── stdlib/
│   ├── operators.py       # Unary/binary operator dispatch
│   ├── matrix.py          # Matrix construction helpers
│   ├── indexing.py        # MATLAB 1-based subscripting ↔ PyTorch 0-based
│   ├── cells.py           # Cell array concatenation
│   └── structs.py         # Struct creation (DictWrapper)
├── types/
│   ├── base.py            # MatraceType (ABC), AnyType (singleton)
│   ├── scalar.py          # ScalarType(dtype)
│   ├── matrix.py          # VectorType, MatrixType
│   ├── cell.py            # CellType
│   ├── struct.py          # StructType
│   ├── function.py        # FunctionType
│   ├── dtypes.py          # Dtype literal + DTYPES frozenset
│   ├── registry.py        # TYPE_REGISTRY + register_type_parser()
│   └── __init__.py        # Re-exports all public types
├── analysis/
│   ├── type_parser.py     # parse_type_str(), extract_func_annotations(), FuncAnnotation
│   └── __init__.py
└── utils/
    ├── context.py         # Stack-based ContextManager
    ├── dict_wrapper.py    # Attribute-access dict wrapper (for structs)
    ├── nested_dict.py     # Nested dictionary helpers
    └── ...
```

## Core Modules

### 1. api/import_func.py – Public Entry Point

**Purpose**: Stable, well-defined API for importing MATLAB functions as Python callables.

**Key Function**: `import_matlab_func(source, *, function_name, scope, is_code, return_ast, compile_mode, type_hints)`

**Signature summary**:
```python
def import_matlab_func(
    source: str | Path,
    *,
    function_name: str | list[str | None] | None = None,
    scope: dict | None = None,
    is_code: bool = False,
    return_ast: bool = False,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: dict | None = None,
) -> Callable | list[Callable] | tuple | list[tuple]:
    ...
```

- `function_name=None` imports the first (or default-named) function.
- `function_name="foo"` imports the function named `"foo"`.
- `function_name=["foo", None, "bar"]` imports three functions; `None` within the list selects the default/first function.
- When `return_ast=False` (default): returns `Callable` (single) or `list[Callable]` (multiple).
- When `return_ast=True`: returns `(Function_Definition, FuncAnnotation, callable)` triples.

**Workflow**:
1. Read MATLAB file or code string
2. Parse with `parser/parser.py`
3. Extract `Function_Definition` AST nodes by name
4. Extract JSDoc type annotations with `analysis/type_parser.py`
5. Wrap each function in a Python callable backed by `interpreter/cfg_executor.py`

### 2. parser/parser.py – MATLAB Parser Wrapper

**Purpose**: Thin wrapper around `miss_hit_core` that returns a `Function_File` / `Script_File` AST.

**Key Function**: `parse_matlab_code(content, path)` → `Function_File | Script_File`

**Key Class**: `ModifiedMessageHandler` – converts fatal parse errors to Python exceptions.

### 3. parser/ast_utils.py – AST Utilities

**Key Function**: `get_function_by_name(ast, name)` → `Function_Definition | None`

### 4. ir/cfg.py – Control Flow Graph

**Purpose**: Convert a MATLAB `Sequence_Of_Statements` into a CFG for execution.

**Key Components**:

#### CFGType Enumeration
Defines node types:
- `SEQUENCE`: Linear statement sequence
- `GLOBAL_ENTRY/EXIT`: Function entry/exit points
- `IF_ENTRY/EXIT/ACTION_ENTRY`: Conditional branches
- `FOR_ENTRY/EXIT/INIT/CONTINUE`: For loop structure
- `WHILE_ENTRY/EXIT/CONTINUE`: While loop structure
- `SWITCH_ENTRY/EXIT/ACTION_ENTRY`: Switch statements
- `TRY_ENTRY/EXIT/CATCH`: Exception handling
- `SPMD_ENTRY/EXIT`: Parallel blocks (parsed, not parallel)
- `BREAK/CONTINUE/RETURN`: Control flow breaks

#### CFGNode
```python
@dataclass
class CFGNode:
    uid: int
    type: int                             # CFGType value
    label: str
    stmt_list: Optional[Sequence_Of_Statements]
```

#### CFGEdge
```python
@dataclass
class CFGEdge:
    from_node: int
    to_node: int
    label: str
    cond: Optional[Expression]            # Condition for edge traversal
    precedence: Optional[int]
```

#### CFG Class
- `nodes`: dict of all CFG nodes
- `edges`: dict mapping node IDs → outgoing edges
- `entry_id / exit_id`
- `add_node()`, `add_edge()`

**Key Function**: `generate_cfg(stmts)` – convert a statement list to a complete CFG.

### 5. ir/ast_visitor.py – AST Visitor Base

**Purpose**: Generic visitor pattern for traversing `miss_hit_core` AST nodes.

**Key Class**: `MatlabAstVisitor` – extensible base for custom AST analysis or transformation.

### 6. interpreter/executor.py – Expression Evaluator

**Purpose**: Evaluate MATLAB expressions and execute simple (non-branching) statements.

**Key Class**: `CodeExecutor`

**Attributes**:
- `vars`: variable bindings dictionary
- `mat_ctx`: `ContextManager` for tracking array dimensions (`end` keyword)

**Core Methods**:
- `eval(node)`: Recursively evaluate an expression (literals, identifiers, operators, subscripts, function calls)
- `subsasgn(node)`: Variable assignment (simple, subscripted, field)
- `exec(node)`: Execute a statement sequence

**Special Features**:
- `MatrixContext`: tracks current array size for `end` resolution
- 1-based ↔ 0-based indexing conversion (transparent)

### 7. interpreter/cfg_executor.py – Control Flow Executor

**Purpose**: Traverse a CFG and execute all nodes, including loops and conditionals.

**Key Function**: `exec_func(func_ast, args, scope)` – entry point called by `import_matlab_func`.

**Key Class**: `CodeControlExecutor` (extends `CodeExecutor`)

**Key Method**: `exec_node(node)` – dispatches on `CFGType`:
- **FOR_INIT / FOR_ENTRY / FOR_EXIT**: Loop setup, iteration, teardown
- **IF / SWITCH**: Evaluate conditions, follow the matching edge
- **TRY / CATCH**: Exception handling

### 8. stdlib/operators.py – Operator Dispatch

**Key Functions**:
- `eval_unary_opr(opr, elem)`: `'`, `.'`, `-`, `~`
- `eval_binary_opr(opr, elem1, elem2)`: arithmetic, comparison, logical

**Implementation Notes**:
- Matrix division uses `torch.inverse()` (known limitation)
- Matrix power uses `torch.linalg.matrix_power()`
- Element-wise operations broadcast naturally

### 9. stdlib/matrix.py – Matrix Construction

**Key Functions**:
- `eval_col_cat(items)`: vertical concatenation `[A; B]`
- `eval_row_cat(items)`: horizontal concatenation `[A, B]`

### 10. stdlib/indexing.py – Subscripting

**Purpose**: MATLAB 1-based subscripting with column-major linear indexing.

**Key Functions**:
- `parse_subsref_arr_slice(sub, is_mono)`: convert MATLAB subscript to PyTorch index
- `gen_torch_slice_by_subsref_slice(subs_parsed, size)`: build 2D index tensors
- `commit_subsref_or_subsasgn_arr(node, subs_parsed, assign_rhs, copy_required)`: read or write array elements

### 11. stdlib/cells.py – Cell Arrays

**Key Functions**: `concat_cells_row`, `concat_cells_col`

**Implementation**: cells are Python `list[list[Any]]`.

### 12. stdlib/structs.py – Structures

**Key Function**: `create_struct(*args, **kwargs)` → `DictWrapper`

### 13. types/ – Type Hierarchy

All types inherit from `MatraceType` (abstract base class).

| Class | Key Attributes |
|---|---|
| `AnyType` | Singleton; represents unknown / dynamic type |
| `ScalarType` | `dtype: "float" \| "int" \| "logical"` |
| `VectorType` | `dtype`, `length: int \| None`, `orientation: "row" \| "col" \| None` |
| `MatrixType` | `dtype`, `rows: int \| None`, `cols: int \| None` |
| `CellType` | `element_type: MatraceType`, `shape` |
| `StructType` | `fields: dict[str, MatraceType]` |
| `FunctionType` | `params: list[MatraceType]`, `returns: list[MatraceType]` |

**Extensibility**: Register new type keywords via `register_type_parser(name, fn)` in `types/registry.py`.

### 14. analysis/type_parser.py – JSDoc Annotation Parser

**Purpose**: Parse type-expression strings and extract `@param`/`@returns` annotations from MATLAB comments.

**Type-string grammar**:
```
type := any
      | scalar <dtype>
      | vector<dim?>  <dtype>
      | matrix<dim,dim?> <dtype>
      | cell<type?>
      | struct<{field: type, …}>
      | <custom keyword>      ← extensible via TYPE_REGISTRY

dtype := float | int | logical
dim   := <integer> | any
```

**Key Public API**:
- `parse_type_str(s)` → `MatraceType`
- `extract_func_annotations(func_ast, source)` → `FuncAnnotation`
- `FuncAnnotation` – dataclass with `params: dict[str, MatraceType]` and `returns: list[MatraceType]`

**Example MATLAB annotation**:
```matlab
% @param {matrix<3,3> float} A - coefficient matrix
% @param {vector<any> float} b
% @returns {vector<any> float}
function x = solve(A, b)
    x = A \ b;
end
```

### 15. utils/context.py – Context Management

**Key Class**: `ContextManager` – push/pop stack for nested scopes (used for loop variables and `end` resolution).

### 16. utils/dict_wrapper.py – Dictionary Wrapper

**Key Class**: `DictWrapper` – provides attribute-style and dict-style access to the same underlying dict (used for MATLAB structs).

```python
s = DictWrapper({'field': 42})
s.field   # 42
s['field']  # 42
```

## Execution Flow

### Complete Pipeline

1. **Parse MATLAB Code** (`parser/parser.py`):
   ```
   MATLAB source → MATLAB_Lexer → MATLAB_Parser → AST (Function_File)
   ```

2. **Extract Function** (`parser/ast_utils.py`):
   ```
   AST → get_function_by_name() → Function_Definition
   ```

3. **Extract Annotations** (`analysis/type_parser.py`):
   ```
   Function_Definition + source → extract_func_annotations() → FuncAnnotation
   ```

4. **Generate CFG** (`ir/cfg.py`):
   ```
   Function_Definition.n_body → generate_cfg() → CFG
   ```

5. **Execute Function** (`interpreter/cfg_executor.py`):
   ```
   CFG + args + scope → CodeControlExecutor → traverse nodes → result
   ```

6. **Evaluate Expressions** (`interpreter/executor.py`):
   ```
   Expression → CodeExecutor.eval() → PyTorch operations
   ```

### Example: Simple Function

```matlab
function y = square(x)
    y = x * x;
end
```

Execution trace:
1. Parse → `Function_Definition` for `square`
2. `import_matlab_func` wraps it in a Python callable
3. Call: `result = square(torch.tensor([[3.0]]))`
4. `exec_func` builds CFG: Entry → Assignment → Exit
5. `eval('x * x')`:
   - Look up `x` in `vars`
   - Call `eval_binary_opr('*', x, x)` → `torch.matmul(x, x)`
6. Assign result to `y`; return `y`

## Design Patterns

### 1. Visitor Pattern
`ir/ast_visitor.py` – extensible AST traversal.

### 2. Context Management
`utils/context.py` – clean stack-based scope management for nested contexts.

### 3. Factory Pattern
CFG nodes and edges created via factory methods in the `CFG` class.

### 4. Strategy Pattern
`exec_node()` dispatches execution strategy based on `CFGType`.

### 5. Registry Pattern
`types/registry.py` – `TYPE_REGISTRY` maps type keywords to parser callables, enabling third-party type extensions without modifying core code.

## Thread Safety

**Current Status**: Not thread-safe.

**Issues**: variable dict, context manager state, no locking.

**Recommendation**: Use separate `CodeControlExecutor` instances for concurrent execution.

## Performance Considerations

### Bottlenecks
1. Dynamic interpretation: every expression evaluated at runtime
2. No expression caching

### Optimization Opportunities
1. **Static compilation**: pre-compute types when `FuncAnnotation` is complete
2. **JIT tracing**: `torch.jit.trace()` after dynamic execution
3. **Type-driven dispatch**: use `FuncAnnotation` to skip runtime type checks

## Extension Points

### Adding New Operators
1. Add case in `eval_binary_opr()` / `eval_unary_opr()` in `stdlib/operators.py`
2. Implement using PyTorch operations
3. Test

### Adding New Statement Types
1. Add `CFGType` constant in `ir/cfg.py`
2. Add CFG-generation logic in `generate_cfg()`
3. Add execution case in `exec_node()` in `interpreter/cfg_executor.py`

### Adding New Type Keywords
```python
from matrace.types.registry import register_type_parser
from matrace.types.base import MatraceType
from dataclasses import dataclass

@dataclass(frozen=True)
class TensorType(MatraceType):
    rank: int = 0

def _parse_tensor(parser):
    parser.consume("LT")
    rank = int(parser.consume("INT")[1])
    parser.consume("GT")
    return TensorType(rank=rank)

register_type_parser("tensor", _parse_tensor)
# Now parse_type_str("tensor<3>") → TensorType(rank=3)
```

### Injecting Built-in Functions
```python
import_matlab_func(
    'script.m',
    scope={
        'sin': torch.sin,
        'cos': torch.cos,
        'sum': lambda x: torch.sum(x, dim=0, keepdim=True),
    }
)
```

## Related Documentation

- `matlab-subset.md`: Supported MATLAB features and known limitations
- `potential-bugs.md`: Known issues and workarounds
- `roadmap.md`: Future development plans
