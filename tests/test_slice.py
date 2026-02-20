import torch

from matrace.stdlib.indexing import eval_subsref_arr


A = torch.tensor([
    [1, 2, 3],
    [4, 5, 6],
])


def test_single():
  assert eval_subsref_arr(A, [1, 2])[0][0] == 2
  assert eval_subsref_arr(A, [2, 2])[0][0] == 5
  assert eval_subsref_arr(A, [5])[0][0] == 3


def test_slice_1():
  # A() == A
  assert (eval_subsref_arr(A, []) == A).all()
  # A(:) = [1;4;2;5;3;6]
  assert (eval_subsref_arr(A, [slice(None)])
          == A.transpose(-2, -1).reshape((-1, 1))).all()
  # A(1:end) = [1 4 2 5 3 6]
  assert (eval_subsref_arr(A, [slice(1, 7, None)])
          == A.transpose(-2, -1).reshape((1, -1))).all()
  # A([1;2;4]) = [1;4;5]
  assert (eval_subsref_arr(A, [torch.tensor([[1], [2], [4]])])
          == torch.tensor([[1], [4], [5]])).all()


def test_slice_2():
  # A(1:end, 2:3) = [2 3; 5 6]
  assert (eval_subsref_arr(A, [slice(1, 3), slice(2, 4)]) == A[:, 1:]).all()
  # A(:, 2:3) = [2 3; 5 6]
  assert (eval_subsref_arr(A, [slice(None), slice(2, 4)]) == A[:, 1:]).all()
  # A(:, 2) = [2;5]
  assert (eval_subsref_arr(A, [slice(None), 2]) == A[:, 1:2]).all()


# --------------------------------------------------------------------------
# Additional tests for Bug #8: column-major linear indexing correctness
# --------------------------------------------------------------------------

def test_linear_index_all():
  """A([1 2 3 4 5 6]) visits elements in column-major order: 1,4,2,5,3,6."""
  expected = torch.tensor([[1, 4, 2, 5, 3, 6]])
  result = eval_subsref_arr(A, [torch.tensor([[1, 2, 3, 4, 5, 6]])])
  assert (result == expected).all()


def test_linear_index_subset():
  """A([1 3 5]) = [1, 2, 3] in column-major order."""
  # Column-major: idx 1→(0,0)=1, idx 3→(0,1)=2, idx 5→(0,2)=3
  result = eval_subsref_arr(A, [torch.tensor([[1, 3, 5]])])
  assert (result == torch.tensor([[1, 2, 3]])).all()


def test_linear_index_col_major_second_row():
  """A([2 4 6]) = [4, 5, 6] (second row in column-major order)."""
  # idx 2→(1,0)=4, idx 4→(1,1)=5, idx 6→(1,2)=6
  result = eval_subsref_arr(A, [torch.tensor([[2, 4, 6]])])
  assert (result == torch.tensor([[4, 5, 6]])).all()


def test_linear_index_column_vector():
  """Linear index as column vector preserves shape."""
  # A([1;3;5]) should give a column vector [[1],[2],[3]]
  result = eval_subsref_arr(A, [torch.tensor([[1], [3], [5]])])
  assert (result == torch.tensor([[1], [2], [3]])).all()
