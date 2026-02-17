# Development Roadmap

This document outlines a comprehensive roadmap for improving matrace to support static analysis, type safety, and better code organization.

## Vision

Transform matrace from a dynamic interpreter into a hybrid system that:
1. **Supports static compilation** when type information is available
2. **Falls back to dynamic interpretation** for dynamically-typed code
3. **Provides clear module boundaries** with import/export analysis
4. **Optimizes memory usage** with copy-on-write analysis
5. **Supports modern development** with type annotations and tooling

## Phase 1: Code Reorganization (Foundation)

**Goal**: Establish clear separation of concerns and modular architecture.

### 1.1 Restructure Module Hierarchy

**Current Structure**:
```
matrace/
├── helper.py
├── exec_flow.py
├── exec_cfg.py
├── mh/
├── std/
└── utils/
```

**Proposed Structure**:
```
matrace/
├── api/                    # Public API
│   └── import_func.py      # Main import function
├── parser/                 # MATLAB parsing
│   ├── lexer.py           # Wrapper around miss_hit lexer
│   ├── parser.py          # Wrapper around miss_hit parser
│   └── ast_utils.py       # AST utilities
├── analysis/              # Static analysis modules
│   ├── type_inference.py  # Type inference engine
│   ├── module_graph.py    # Import/export analysis
│   ├── cow_analysis.py    # Copy-on-write detection
│   └── class_analyzer.py  # Class structure analysis
├── ir/                    # Intermediate representation
│   ├── cfg.py            # Control flow graph (moved from mh/)
│   ├── ast_visitor.py    # AST visitor (moved from mh/)
│   └── typed_ast.py      # Type-annotated AST
├── compiler/             # Static compilation
│   ├── codegen.py        # Generate PyTorch code
│   ├── optimizer.py      # IR optimization passes
│   └── torch_backend.py  # PyTorch code generation
├── interpreter/          # Dynamic execution
│   ├── executor.py       # Main interpreter (exec_flow.py)
│   ├── cfg_executor.py   # CFG interpreter (exec_cfg.py)
│   └── context.py        # Execution context
├── stdlib/               # Standard library (renamed from std/)
│   ├── operators.py      # Operators (opr.py)
│   ├── matrix.py         # Matrix ops (mat_opr.py)
│   ├── indexing.py       # Indexing (mat_subs.py)
│   ├── cells.py          # Cell arrays (cell_opr.py)
│   └── structs.py        # Structures (struct.py)
├── types/                # Type system
│   ├── base.py           # Base type classes
│   ├── matrix_type.py    # Matrix type system
│   ├── cell_type.py      # Cell array types
│   └── struct_type.py    # Struct types
└── utils/                # Utilities (keep existing)
```

**Benefits**:
- Clear separation: parsing, analysis, compilation, interpretation
- Easy to add new analysis passes
- Testable module boundaries
- Supports gradual migration

**Implementation Steps**:
1. Create new directory structure
2. Move existing files to new locations
3. Update import statements
4. Ensure tests still pass
5. Update documentation

**Estimated Effort**: 2-3 weeks

### 1.2 Define Public API Contract

**Current Issue**: `helper.py` is the main API but not well-defined.

**Proposed API** (`matrace/api/import_func.py`):
```python
def import_matlab_func(
    source: str | Path,
    *,
    function_name: str | List[str] | None = None,
    scope: Dict[str, Any] | None = None,
    is_code: bool = False,
    return_ast: bool = False,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: Dict[str, TypeHint] | None = None,
) -> Callable | List[Callable]:
    """
    Import MATLAB function(s) as Python callables.
    
    Args:
        source: File path or code string
        function_name: Name(s) of function(s) to import
        scope: External functions to inject
        is_code: True if source is code string, False if file path
        return_ast: Return (AST, callable) tuples
        compile_mode: 
            - "auto": Use static if types available, else dynamic
            - "static": Force static compilation (error if types missing)
            - "dynamic": Force dynamic interpretation
        type_hints: Optional type hints for parameters
    
    Returns:
        Callable or list of callables
    """
    pass
```

**Benefits**:
- Clear contract for users
- Extensibility for new features
- Backward compatibility path

**Estimated Effort**: 1 week

## Phase 2: Type System Implementation

**Goal**: Introduce a type system to enable static analysis and optimization.

### 2.1 Design Type Hierarchy

**Base Types**:
```python
# matrace/types/base.py
class MatraceType:
    """Base class for all matrace types."""
    pass

class ScalarType(MatraceType):
    """Scalar number or logical."""
    dtype: Literal["float", "int", "logical"]

class VectorType(MatraceType):
    """Row or column vector."""
    orientation: Literal["row", "col"]
    length: int | None  # None = variable length
    dtype: Literal["float", "int", "logical"]

class MatrixType(MatraceType):
    """Matrix (2D array)."""
    rows: int | None    # None = variable
    cols: int | None    # None = variable
    dtype: Literal["float", "int", "logical"]

class CellType(MatraceType):
    """Cell array."""
    element_type: MatraceType  # Type of elements (can be Any)
    shape: Tuple[int | None, int | None]

class StructType(MatraceType):
    """Structure with named fields."""
    fields: Dict[str, MatraceType]

class FunctionType(MatraceType):
    """Function signature."""
    params: List[MatraceType]
    returns: List[MatraceType]

class AnyType(MatraceType):
    """Unknown/dynamic type."""
    pass
```

**Example Usage**:
```python
# x is a 3×3 matrix of floats
x_type = MatrixType(rows=3, cols=3, dtype="float")

# y is a variable-length column vector
y_type = VectorType(orientation="col", length=None, dtype="float")
```

**Estimated Effort**: 2 weeks

### 2.2 Implement JSDoc-Style Type Annotations

**Goal**: Allow users to annotate MATLAB code with type hints in comments.

**Syntax Design** (similar to JSDoc/TypeDoc):
```matlab
% @param {scalar float} x - Input value
% @param {matrix<3,3> float} A - 3x3 matrix
% @returns {scalar float} - Result
function y = my_func(x, A)
    y = x * sum(A(:));
end
```

**Type Annotation Grammar**:
```
type := scalar <dtype>
      | vector<length?> <dtype>
      | matrix<rows?,cols?> <dtype>
      | cell<type?>
      | struct<{field: type, ...}>
      | any

dtype := float | int | logical
```

**Examples**:
```matlab
% @param {matrix<any,any> float} A - Variable-size matrix
% @param {vector<any> float} b - Variable-length vector
% @returns {matrix<any,any> float}
function x = solve(A, b)
    x = A \ b;
end

% @param {cell<scalar float>} C - Cell array of scalars
% @returns {scalar float}
function s = sum_cells(C)
    s = 0;
    for i = 1:length(C)
        s = s + C{i};
    end
end
```

**Implementation**:
1. **Parser**: Extract type hints from comments before/after function signature
2. **Validator**: Verify type annotation syntax
3. **Type Builder**: Construct `MatraceType` objects from annotations

**Module**: `matrace/analysis/type_parser.py`

**Estimated Effort**: 3 weeks

### 2.3 Type Inference Engine

**Goal**: Infer types for unannotated code when possible.

**Algorithm**:
1. **Forward pass**: Propagate types from inputs through expressions
2. **Constraint generation**: Generate type constraints from operations
3. **Constraint solving**: Solve constraints to determine minimal types
4. **Backward pass**: Propagate inferred types back to verify consistency

**Example**:
```matlab
function y = infer_example(x)
    % No annotations
    y = x + 1;  % Infer: x is numeric, y is same type as x
end
```

**Inference Rules**:
- Binary ops: `MatrixType(m,n) + MatrixType(m,n) → MatrixType(m,n)`
- Matrix multiply: `MatrixType(m,n) * MatrixType(n,p) → MatrixType(m,p)`
- Indexing: `MatrixType(m,n)[i,j] → ScalarType`
- Loops: Infer from range expression

**Module**: `matrace/analysis/type_inference.py`

**Estimated Effort**: 4-6 weeks

## Phase 3: Static Compilation Support

**Goal**: Generate optimized PyTorch code when types are known.

### 3.1 Design Intermediate Representation (IR)

**Goal**: Create a typed IR suitable for optimization.

**IR Structure**:
```python
# matrace/ir/typed_ast.py
class TypedNode:
    """Base class for typed IR nodes."""
    type: MatraceType
    source_location: SourceLocation

class TypedExpr(TypedNode):
    pass

class TypedStmt(TypedNode):
    pass

class TypedBinaryOp(TypedExpr):
    operator: str
    left: TypedExpr
    right: TypedExpr

class TypedAssignment(TypedStmt):
    target: str
    value: TypedExpr
```

**Transformation Pipeline**:
```
MATLAB AST → Typed IR → Optimized IR → PyTorch Code
```

**Estimated Effort**: 3 weeks

### 3.2 Implement Code Generator

**Goal**: Generate efficient PyTorch code from typed IR.

**Example**:
```matlab
% Input MATLAB
function y = matrix_multiply(A, B)
    % @param {matrix<10,10> float} A
    % @param {matrix<10,10> float} B
    % @returns {matrix<10,10> float}
    y = A * B;
end
```

**Generated PyTorch Code**:
```python
def matrix_multiply(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Generated from MATLAB.
    A: (10, 10) float tensor
    B: (10, 10) float tensor
    Returns: (10, 10) float tensor
    """
    # A * B (matrix multiplication)
    y = torch.matmul(A, B)
    return y
```

**Code Generation Rules**:
- Direct mapping of typed operations to PyTorch
- Static shape verification
- Inline type assertions for safety
- Preserve 1-based indexing conversion

**Module**: `matrace/compiler/codegen.py`

**Estimated Effort**: 4 weeks

### 3.3 Optimization Passes

**Goal**: Optimize IR before code generation.

**Proposed Optimizations**:

1. **Constant Folding**: Evaluate compile-time constants
   ```matlab
   y = 2 * 3 + 4;  % → y = 10;
   ```

2. **Dead Code Elimination**: Remove unused variables
   ```matlab
   x = 5;  % x never used
   y = 10;
   ```

3. **Loop Unrolling**: Unroll fixed-length loops
   ```matlab
   for i = 1:3
       A(i) = i;
   end
   % → A(1) = 1; A(2) = 2; A(3) = 3;
   ```

4. **Operator Fusion**: Combine operations
   ```matlab
   y = (A + B) * C;  % Fuse into single kernel
   ```

5. **Memory Reuse**: Reuse temporary buffers

**Module**: `matrace/compiler/optimizer.py`

**Estimated Effort**: 4-6 weeks

### 3.4 Hybrid Execution Strategy

**Goal**: Seamlessly mix static and dynamic code.

**Strategy**:
```python
def execute(func_ast, args):
    if has_complete_type_info(func_ast):
        # Static compilation
        compiled_func = compile_to_pytorch(func_ast)
        return compiled_func(*args)
    else:
        # Dynamic interpretation
        return interpret_dynamically(func_ast, args)
```

**Partial Compilation**: Compile typed portions, interpret rest
```matlab
function y = hybrid(x)
    % @param {matrix<10,10> float} x
    A = x * x;           % Statically compiled
    B = some_func(A);    % Dynamically interpreted (unknown type)
    y = B + 1;           % Back to static
end
```

**Estimated Effort**: 3 weeks

## Phase 4: Module System and Dependency Analysis

**Goal**: Support multi-file MATLAB projects with proper dependency tracking.

### 4.1 Import/Export Analysis

**Goal**: Analyze which functions/variables each module provides and uses.

**Module Graph**:
```python
# matrace/analysis/module_graph.py
class ModuleNode:
    path: Path
    functions_defined: Set[str]
    functions_called: Set[str]
    variables_exported: Set[str]
    dependencies: Set[ModuleNode]

class ModuleGraph:
    nodes: Dict[Path, ModuleNode]
    
    def add_module(self, path: Path):
        """Add module to graph."""
        
    def analyze_dependencies(self):
        """Build dependency graph."""
        
    def topological_sort(self) -> List[ModuleNode]:
        """Return modules in dependency order."""
```

**Use Cases**:
1. Import multiple related MATLAB files
2. Detect circular dependencies
3. Optimize compilation order
4. Generate import statements

**Example**:
```matlab
% utils.m
function y = square(x)
    y = x * x;
end

% main.m
function result = main(x)
    result = square(x) + 1;  % Calls square from utils.m
end
```

**Analysis Output**:
```
main.m depends on utils.m
  - calls: square
```

**Estimated Effort**: 3 weeks

### 4.2 Cross-File Type Propagation

**Goal**: Propagate type information across module boundaries.

**Example**:
```matlab
% lib.m
% @returns {matrix<5,5> float}
function A = get_matrix()
    A = rand(5, 5);
end

% main.m
function y = process()
    A = get_matrix();  % Type inferred: matrix<5,5> float
    y = A * A;         % Can be statically compiled
end
```

**Implementation**:
1. Collect type signatures from all modules
2. Build type environment
3. Resolve cross-module type dependencies

**Estimated Effort**: 2 weeks

## Phase 5: Copy-on-Write Analysis

**Goal**: Automatically determine when copies are needed vs. when references are safe.

### 5.1 Alias Analysis

**Goal**: Track which variables may alias the same data.

**Algorithm**:
1. Build alias graph: which variables reference same data
2. Track mutations: when variables are modified
3. Determine copy points: where copies must be made

**Example**:
```matlab
A = [1 2; 3 4];
B = A;           % B aliases A
B(1,1) = 10;     % Mutation: copy needed here
```

**Analysis Output**:
```
Line 2: B = A.clone()  % Insert copy
```

**Module**: `matrace/analysis/cow_analysis.py`

**Estimated Effort**: 4 weeks

### 5.2 In-Place Operation Detection

**Goal**: Detect when operations can be done in-place safely.

**Example**:
```matlab
A = rand(100);
A = A + 1;      % Can be in-place: A += 1
```

**Detection Rules**:
- Variable not used after modification
- No aliases exist
- Operation supports in-place variant

**Benefits**:
- Reduced memory usage
- Faster execution
- Better GPU utilization

**Estimated Effort**: 2 weeks

## Phase 6: Class Support

**Goal**: Support MATLAB class definitions (without advanced OOP).

### 6.1 Class Structure Analysis

**Scope**: Support basic classes with properties and methods.

**Not Supported** (initially):
- Inheritance
- Operator overloading
- Abstract classes
- Events and listeners

**Example**:
```matlab
classdef MyClass
    properties
        x
        y
    end
    
    methods
        function obj = MyClass(x, y)
            obj.x = x;
            obj.y = y;
        end
        
        function r = compute(obj)
            r = obj.x + obj.y;
        end
    end
end
```

**Representation**:
```python
class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def compute(self):
        return self.x + self.y
```

**Module**: `matrace/analysis/class_analyzer.py`

**Estimated Effort**: 4-6 weeks

### 6.2 Type Annotations for Classes

**JSDoc-Style Class Annotations**:
```matlab
classdef MyClass
    properties
        % @type {matrix<3,3> float}
        A
        
        % @type {scalar float}
        scale
    end
    
    methods
        % @param {matrix<3,3> float} A
        % @param {scalar float} scale
        function obj = MyClass(A, scale)
            obj.A = A;
            obj.scale = scale;
        end
    end
end
```

**Estimated Effort**: 2 weeks

## Phase 7: Developer Experience

**Goal**: Improve tooling and documentation.

### 7.1 Better Error Messages

**Current**: Generic exceptions with poor context
**Target**: Clear, actionable error messages

**Example**:
```
Error in my_func.m, line 15, column 8:
    y = x * z;
        ^^^^^
Type mismatch: cannot multiply matrix<3,4> with matrix<5,6>
Expected second operand to have 4 rows, got 5
```

**Estimated Effort**: 2 weeks

### 7.2 Documentation and Examples

**Deliverables**:
1. User guide with examples
2. API reference
3. Type annotation guide
4. Migration guide for existing code
5. Tutorial notebooks

**Estimated Effort**: 3 weeks

### 7.3 Debugging Tools

**Features**:
1. Step-through debugger for MATLAB code
2. Variable inspector
3. Breakpoint support
4. Execution trace visualization

**Estimated Effort**: 4 weeks

## Implementation Timeline

### Short-term (0-6 months)
- **Month 1-2**: Phase 1 (Code reorganization)
- **Month 3-4**: Phase 2.1-2.2 (Type system, annotations)
- **Month 5-6**: Phase 2.3 (Type inference basics)

### Medium-term (6-12 months)
- **Month 7-8**: Phase 3.1-3.2 (IR and code generation)
- **Month 9-10**: Phase 4.1 (Module analysis)
- **Month 11-12**: Phase 5.1 (Copy-on-write basics)

### Long-term (12+ months)
- **Month 13-14**: Phase 3.3 (Optimizations)
- **Month 15-16**: Phase 6 (Class support)
- **Month 17-18**: Phase 7 (Developer experience)

## Backward Compatibility

### Migration Strategy

**Goal**: Existing code continues to work unchanged.

**Approach**:
1. Keep dynamic interpreter as default
2. Opt-in to static compilation via mode flag
3. Gradual type annotation adoption
4. Provide compatibility layer

**Example**:
```python
# Old code - still works
func = import_matlab_func('old_script.m')

# New code - with types and static compilation
func = import_matlab_func(
    'new_script.m',
    compile_mode='static',  # Opt-in
    type_hints={'x': MatrixType(10, 10)}
)
```

## Testing Strategy

### Test Categories

1. **Unit Tests**: Each component tested independently
2. **Integration Tests**: Full pipeline tests
3. **Regression Tests**: Existing functionality preserved
4. **Performance Tests**: Benchmark static vs. dynamic
5. **Type System Tests**: Type inference correctness

### Test Coverage Goals

- Core modules: 90%+
- Type system: 95%+
- Code generation: 85%+

## Success Metrics

### Performance
- **Static compilation**: 5-10× faster than dynamic interpretation
- **Memory usage**: 30-50% reduction with copy-on-write

### Developer Experience
- **Type errors**: 80%+ caught at compile time (with annotations)
- **Error messages**: 90%+ actionable errors

### Adoption
- **Type annotations**: Easy to add, clear benefits
- **Migration**: Smooth path from dynamic to static

## Future Enhancements (Beyond Roadmap)

### Advanced Features
1. **GPU optimization**: Automatic kernel fusion
2. **Quantization**: Mixed-precision types
3. **Sparse matrices**: Sparse tensor support
4. **Symbolic computation**: Integration with SymPy
5. **Neural network patterns**: Recognize and optimize NN layers

### Tooling
1. **IDE plugin**: VSCode/MATLAB editor integration
2. **Linter**: Static analysis for MATLAB code
3. **Auto-formatter**: Code style enforcement
4. **Package manager**: Dependency management

### Ecosystem
1. **Standard library**: Common MATLAB functions
2. **Community contributions**: Plugin system
3. **Interoperability**: MATLAB/Python bridge
4. **Benchmarks**: Performance comparison suite

## Conclusion

This roadmap provides a clear path to transform matrace from a basic interpreter into a sophisticated MATLAB-to-PyTorch compiler with:
- Strong type safety through annotations and inference
- Efficient static compilation where possible
- Graceful fallback to dynamic interpretation
- Clear module boundaries and dependency management
- Memory-efficient copy-on-write semantics
- Basic class support for structured programs

The phased approach allows incremental implementation while maintaining backward compatibility and delivering value at each stage.
