import torch

from matrace.std.mat_subs import eval_subsref_arr


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
