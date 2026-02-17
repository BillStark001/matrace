# Documentation Index

Welcome to the Matrace documentation. This index helps you navigate the available documentation.

## Getting Started

If you're new to Matrace, start here:

1. **[README](../README.md)** - Quick start guide with installation and basic examples
2. **[MATLAB Subset Definition](matlab-subset.md)** - Learn what MATLAB features are supported

## Core Documentation

### For Users

- **[MATLAB Subset Definition](matlab-subset.md)** - Complete reference of supported MATLAB language features
  - Data types (matrices, cells, structs, strings)
  - Operators (arithmetic, logical, comparison)
  - Control flow (if, for, while, switch)
  - Indexing and subscripting
  - Limitations and recommendations

### For Developers

- **[Architecture Guide](architecture.md)** - Internal design and implementation
  - Module structure and organization
  - Execution pipeline (parsing → CFG → interpretation)
  - Key classes and their responsibilities
  - Extension points for new features

- **[Known Issues](potential-bugs.md)** - Current limitations and bugs
  - Critical issues (copy-on-write, N-D arrays)
  - Type system limitations
  - Indexing edge cases
  - Performance bottlenecks
  - Testing gaps

- **[Development Roadmap](roadmap.md)** - Future plans and vision
  - Code reorganization plan
  - Type system design (JSDoc-style annotations)
  - Static compilation support
  - Module system and dependency analysis
  - Copy-on-write optimization
  - Class support
  - Timeline and milestones

## Quick Reference

### Common Tasks

**Import a MATLAB function**:
```python
from matrace import import_matlab_func
func = import_matlab_func('my_script.m')
```

**Inject custom functions**:
```python
func = import_matlab_func('script.m', scope={
    'sum': lambda x: torch.sum(x).unsqueeze(0).unsqueeze(0)
})
```

**Import multiple functions**:
```python
funcs = import_matlab_func('library.m', function_name=['f1', 'f2'])
f1, f2 = funcs
```

### Supported MATLAB Features Summary

✅ **Fully Supported**:
- Numerical and logical matrices (2D)
- Basic operators (+, -, *, .*, /, ./, ^, .^, <, >, ==, &, |, ~)
- Control flow (if/else, for, while, switch/case)
- Array indexing with 1-based conversion
- Cell arrays
- Structures
- Function definitions with multiple inputs/outputs

⚠️ **Limited Support**:
- Strings (basic only)
- SPMD blocks (parsed but not parallel)
- N-dimensional arrays (3D+)

❌ **Not Supported**:
- Classes and OOP
- Function handles/anonymous functions
- Advanced string operations
- Parallel computing (parfor, spmd execution)

See [matlab-subset.md](matlab-subset.md) for complete details.

## Documentation Structure

```
docs/
├── README.md              # This file
├── matlab-subset.md       # MATLAB language subset reference
├── architecture.md        # Internal architecture and design
├── potential-bugs.md      # Known issues and limitations
└── roadmap.md            # Future development plans
```

## Contributing to Documentation

Documentation improvements are welcome! When contributing:

1. **Keep it concise**: Be clear and to the point
2. **Use examples**: Code examples help understanding
3. **Be accurate**: Verify claims against actual implementation
4. **Update multiple docs**: Related changes may affect multiple files
5. **Follow style**: Match existing formatting and tone

## Related Resources

- **GitHub Repository**: https://github.com/billstark001/matrace
- **Issue Tracker**: https://github.com/billstark001/matrace/issues
- **Test Examples**: See `tests/matlab_examples/` for working examples

## Version

This documentation is for Matrace v0.1.0 (current development version).

Last updated: 2026-02-17
