# Matrace

**MATLAB to PyTorch Compiler** - Transform MATLAB numerical functions into differentiable PyTorch computational graphs.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

Matrace is a compiler that converts a numerical computing-oriented subset of MATLAB into executable PyTorch functions. This enables:

- **Direct integration** of MATLAB models into Python deep learning pipelines
- **Differentiable execution** via PyTorch's autograd for gradient-based optimization
- **System identification** and controller parameter tuning using existing MATLAB code
- **Hybrid workflows** combining MATLAB domain expertise with Python ML ecosystem (PIML, etc.)

## Key Features

- ✅ **MATLAB Subset Support**: Matrices, cells, structs, control flow (if/for/while), operators
- ✅ **PyTorch Backend**: All operations mapped to PyTorch tensors for GPU acceleration
- ✅ **Dynamic Interpretation**: Handles dynamically-typed MATLAB code at runtime
- ✅ **Function Injection**: Seamlessly inject Python/PyTorch functions into MATLAB scope
- 🚧 **Type Annotations** (Planned): JSDoc-style type hints for optimization
- 🚧 **Static Compilation** (Planned): Generate optimized code when types are known

## Quick Start

### Installation

```bash
pip install matrace
```

Or install from source:
```bash
git clone https://github.com/billstark001/matrace.git
cd matrace
pip install -e .
```

### Basic Usage

**MATLAB code** (`example.m`):
```matlab
function [result1, result2] = matrix_ops(A, B)
    result1 = A * B;        % Matrix multiplication
    result2 = A .* B;       % Element-wise multiplication
end
```

**Python usage**:
```python
import torch
from matrace import import_matlab_func

# Import MATLAB function
matrix_ops = import_matlab_func('example.m')

# Call with PyTorch tensors
A = torch.randn(3, 3)
B = torch.randn(3, 3)
result1, result2 = matrix_ops(A, B)

# Results are PyTorch tensors, support autograd
loss = result1.sum()
loss.backward()  # Gradients computed through MATLAB operations!
```

### Advanced: Function Injection

Inject custom Python functions into MATLAB scope:

```python
func = import_matlab_func(
    'my_script.m',
    scope={
        'sum': lambda x: torch.sum(x).unsqueeze(0).unsqueeze(0),
        'sqrt': torch.sqrt,
        'sin': torch.sin
    }
)
```

### Multiple Functions

Import multiple functions from one file:

```python
funcs = import_matlab_func(
    'library.m',
    function_name=['func1', 'func2', 'func3']
)
func1, func2, func3 = funcs
```

## Supported MATLAB Features

### Data Types
- **Matrices**: Scalars, vectors, 2D arrays (numerical and logical)
- **Cell Arrays**: Heterogeneous data containers
- **Structures**: Named fields with dot notation access
- **Strings**: Character arrays and string literals

### Operators
- **Arithmetic**: `+`, `-`, `.*`, `*`, `./`, `/`, `.^`, `^`, `.\`, `\`
- **Logical**: `&`, `&&`, `|`, `||`, `~`, `!`
- **Comparison**: `<`, `>`, `<=`, `>=`, `==`, `~=`
- **Unary**: `'` (transpose), `.'` (conjugate transpose), `-`, `~`

### Control Flow
- `if`/`elseif`/`else` statements
- `for` loops (range and iterator)
- `while` loops
- `switch`/`case` statements
- `try`/`catch` exception handling
- `break`/`continue`

### Indexing
- Array subscripting: `A(i,j)`, `A(1:end, :)`
- Cell indexing: `C{i,j}`
- Struct field access: `s.field`
- 1-based MATLAB indexing (automatically converted)

### Limitations
- No classes (planned for future)
- No function handles/anonymous functions (use scope injection)
- 2D arrays only (N-D support limited)
- Basic string operations

For complete details, see [MATLAB Subset Documentation](docs/matlab-subset.md).

## Examples

### Example 1: Element-wise Operations

**MATLAB** (`element_wise.m`):
```matlab
function [result1, result2, result3] = element_wise_operations(A, B)
    result1 = A .* B;      % Element-wise multiplication
    result2 = A > B;       % Element-wise comparison
    result3 = sum(A(:));   % Sum all elements
end
```

**Python**:
```python
import torch
from matrace import import_matlab_func

element_wise = import_matlab_func(
    'element_wise.m',
    scope={'sum': lambda x: torch.sum(x).unsqueeze(0).unsqueeze(0)}
)

A = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
B = torch.tensor([[2.0, 1.0], [2.0, 2.0]])

r1, r2, r3 = element_wise(A, B)
# r1: [[2., 2.], [6., 8.]]
# r2: [[False, True], [True, True]]
# r3: [[10.]]
```

### Example 2: Control Flow

**MATLAB** (`control_flow.m`):
```matlab
function result = for_loop_sum(n)
    result = 0;
    for i = 1:n
        result = result + i;
    end
end
```

**Python**:
```python
sum_func = import_matlab_func('control_flow.m', function_name='for_loop_sum')
result = sum_func(torch.tensor([[5.0]]))  # Sum from 1 to 5
# result: [[15.]]
```

### Example 3: ODE Integration

See `tests/matlab_examples/ode_lorenz.m` for a complete example of integrating ODEs with `torchdiffeq`.

## Architecture

Matrace uses a multi-stage pipeline:

```
MATLAB Source → Parser → AST → CFG → Interpreter → PyTorch Ops
```

**Key Components**:
1. **Parser** (`helper.py`): Uses `miss_hit_core` to parse MATLAB
2. **AST/CFG** (`mh/`): Abstract syntax tree and control flow graph
3. **Interpreter** (`exec_*.py`): Dynamic code execution engine
4. **Standard Library** (`std/`): PyTorch implementations of MATLAB operations

For detailed architecture, see [Architecture Documentation](docs/architecture.md).

## Documentation

- **[MATLAB Subset Definition](docs/matlab-subset.md)**: Complete reference of supported features
- **[Architecture Guide](docs/architecture.md)**: Internal design and module structure
- **[Known Issues](docs/potential-bugs.md)**: Limitations and potential bugs
- **[Development Roadmap](docs/roadmap.md)**: Future plans and enhancements

## Testing

Run the test suite:
```bash
pytest tests/
```

Example test files:
- `tests/test_math.py`: Basic arithmetic and matrix operations
- `tests/test_flow.py`: Control flow (if/for/while)
- `tests/test_cell.py`: Cell array operations
- `tests/test_ode.py`: ODE integration examples

## Roadmap

### Current Status (v0.1.0)
- ✅ Dynamic interpretation of MATLAB subset
- ✅ PyTorch tensor operations
- ✅ Basic control flow support

### Planned Features
- **Type Annotations**: JSDoc-style type hints in MATLAB comments
- **Static Compilation**: Generate optimized PyTorch code when types are known
- **Copy-on-Write Analysis**: Optimize memory usage
- **Module System**: Multi-file project support
- **Class Support**: Basic MATLAB classes (no inheritance initially)
- **Better Error Messages**: Clear, actionable diagnostics

See [Roadmap](docs/roadmap.md) for detailed timeline and implementation plan.

## Contributing

Contributions are welcome! Areas for improvement:

1. **Expand MATLAB support**: Add more operators, functions, or features
2. **Fix bugs**: See [Known Issues](docs/potential-bugs.md)
3. **Add tests**: Increase coverage and edge case testing
4. **Documentation**: Improve examples and tutorials
5. **Performance**: Optimize hot paths and add benchmarks

Please open issues for bugs or feature requests, and PRs for contributions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use Matrace in your research, please cite:

```bibtex
@software{matrace2023,
  title={Matrace: MATLAB to PyTorch Compiler},
  author={Stark, Bill},
  year={2023},
  url={https://github.com/billstark001/matrace}
}
```

## Acknowledgments

- **miss_hit_core**: MATLAB parser and lexer
- **PyTorch**: Tensor computation and automatic differentiation
- Community contributors and users

## Contact

- GitHub Issues: [matrace/issues](https://github.com/billstark001/matrace/issues)
- Maintainer: [@billstark001](https://github.com/billstark001)

---

**Note**: This is a research project. While functional, it may have limitations for production use. See [Known Issues](docs/potential-bugs.md) for details.
