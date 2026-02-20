import pytest
import torch

from matrace.api.import_func import import_matlab_func
from matrace.stdlib.operators import eval_binary_opr

element_wise_operations = import_matlab_func(
    './tests/matlab_examples/element_wise_operations.m',
    scope={
        'sum': lambda x: torch.sum(x).unsqueeze(0).unsqueeze(0)
    }
)

matrix_operations = import_matlab_func(
  './tests/matlab_examples/matrix_operations.m',
)

matrix_div_power = import_matlab_func(
  './tests/matlab_examples/matrix_div_power.m',
)

t = torch.tensor


def test_ew_1():
  # Test case 1: Simple 2x2 arrays
  A1 = t([[1, 2], [3, 4]])
  B1 = t([[2, 1], [2, 2]])
  r1, r2, r3 = element_wise_operations(A1, B1)
  assert torch.equal(r1, t([[2, 2], [6, 8]]))
  assert torch.equal(r2, t([[False, True], [True, True]]))
  assert r3[0, 0] == 10


def test_ew_2():
  # Test case 2: Arrays with zeros
  A2 = t([[0, 1], [0, 0]])
  B2 = t([[1, 1], [1, 0]])
  r1, r2, r3 = element_wise_operations(A2, B2)
  assert torch.equal(r1, t([[0, 1], [0, 0]]))
  assert torch.equal(r2, t([[False, False], [False, False]]))
  assert r3[0, 0] == 1


def test_ew_3():
  # Test case 3: Arrays with negative numbers
  A3 = t([[-1, 2], [-3, 4]])
  B3 = t([[1, -1], [3, 2]])
  r1, r2, r3 = element_wise_operations(A3, B3)
  assert torch.equal(r1, t([[-1, -2], [-9, 8]]))
  assert torch.equal(r2, t([[False, True], [False, True]]))
  assert r3[0, 0] == 2

def test_mat_1():
  A3 = t([[-1, 2], [-3, 4]])
  B3 = t([[1, -1], [3, 2]])
  r1, r2, r3 = matrix_operations(A3, B3)
  assert torch.equal(r1, A3 @ B3)
  assert torch.equal(r2, A3.transpose(0, 1))
  assert torch.equal(r3, t([[3]]))


# --------------------------------------------------------------------------
# Tests for Bug #18: matrix division (mldivide / mrdivide)
# --------------------------------------------------------------------------

def test_mldivide_direct():
  """A \\ b  (solve A*x = b) — using eval_binary_opr directly."""
  A = t([[2., 1.], [1., 3.]])
  b = t([[5.], [10.]])
  x = eval_binary_opr('\\', A, b)
  assert torch.allclose(A @ x, b, atol=1e-5)


def test_mrdivide_direct():
  """b / A  (solve x*A = b) — using eval_binary_opr directly."""
  A = t([[2., 1.], [1., 3.]])
  b = t([[5., 10.]])
  x = eval_binary_opr('/', b, A)
  assert torch.allclose(x @ A, b, atol=1e-5)


def test_mldivide_via_matlab():
  """A \\ b via the MATLAB function fixture."""
  A = t([[3., 1.], [1., 2.]]).double()
  b = t([[9.], [8.]]).double()
  # Solve: 3x1+x2=9, x1+2x2=8  =>  x = [2, 3]
  x_expected = t([[2.], [3.]]).double()
  result1, _, _, _, _ = matrix_div_power(A, b, b, t([[1.]]).double())
  assert torch.allclose(result1, x_expected, atol=1e-5)


def test_mrdivide_via_matlab():
  """b' / A via the MATLAB function fixture (b is column vector, fixture transposes it)."""
  A = t([[1., 0.], [0., 2.]]).double()
  b = t([[3.], [4.]]).double()
  # MATLAB: b' / A = [[3, 4]] / diag([1, 2]) = [[3/1, 4/2]] = [[3, 2]]
  _, result2, _, _, _ = matrix_div_power(A, b, b, t([[1.]]).double())
  assert torch.allclose(result2, t([[3., 2.]]).double(), atol=1e-4)


# --------------------------------------------------------------------------
# Tests for Bug #19: matrix power (mpower) integer casting
# --------------------------------------------------------------------------

def test_scalar_power_integer():
  """Scalar ^ integer exponent."""
  A = t([[1., 0.], [0., 1.]]).double()
  b = t([[1.], [1.]]).double()
  s = t([[3.]]).double()
  _, _, result3, _, _ = matrix_div_power(A, b, b, s)
  assert torch.allclose(result3, t([[27.]]).double(), atol=1e-6)


def test_matrix_power_integer():
  """Matrix ^ 2 — uses torch.linalg.matrix_power."""
  A = t([[1., 2.], [3., 4.]]).double()
  b = t([[1.], [1.]]).double()
  _, _, _, result4, _ = matrix_div_power(A, b, b, t([[1.]]).double())
  assert torch.allclose(result4, A @ A, atol=1e-5)


def test_matrix_power_fractional_raises():
  """Matrix ^ non-integer exponent should raise NotImplementedError."""
  A = t([[4., 0.], [0., 9.]]).double()
  b = t([[0.5]])
  with pytest.raises(NotImplementedError, match=r'fractional exponent'):
    eval_binary_opr('^', A, b)


def test_scalar_power_float():
  """Scalar ^ fractional exponent (element-wise) should work."""
  s = t([[4.]])
  result = eval_binary_opr('^', s, t([[0.5]]))
  assert torch.allclose(result, t([[2.]]), atol=1e-5)


def test_matrix_power_zero():
  """Matrix ^ 0 should give identity."""
  A = t([[2., 3.], [1., 4.]]).double()
  result = eval_binary_opr('^', A, t([[0.]]))
  assert torch.allclose(result, torch.eye(2, dtype=torch.double), atol=1e-6)


def test_matrix_power_negative():
  """Matrix ^ -1 should give inverse."""
  A = t([[2., 1.], [1., 2.]]).double()
  result = eval_binary_opr('^', A, t([[-1.]]))
  expected = torch.linalg.inv(A)
  assert torch.allclose(result, expected, atol=1e-5)
