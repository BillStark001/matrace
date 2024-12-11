import torch

from matrace.helper import import_matlab_func

element_wise_operations = import_matlab_func(
    './tests/matlab_examples/element_wise_operations.m',
    scope={
        'sum': lambda x: torch.sum(x).unsqueeze(0).unsqueeze(0)
    }
)

matrix_operations = import_matlab_func(
    './tests/matlab_examples/matrix_operations.m',
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
  r1, r2, r3, r4 = matrix_operations(A3, B3)
  assert torch.equal(r1, A3 @ B3)
  assert torch.equal(r2, A3.transpose(0, 1))
  assert torch.equal(r3, t([[3]]))
  assert tuple(r4.shape) == (4, 1)
  
