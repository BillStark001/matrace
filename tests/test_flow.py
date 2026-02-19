import torch

from matrace.api.import_func import import_matlab_func

functions = import_matlab_func(
    './tests/matlab_examples/basic_functions.m',
    function_name=['basic', 'array', 'cell',
                   'if_flow', 'for_flow', 'while_flow']
)

f_basic, f_array, f_cell, f_if, f_for, f_while = functions


def test_basic():
  assert f_basic()[0, 0] == 42


def test_array():
  assert torch.equal(
      f_array(),
      torch.tensor([[1, 2], [3, 4]])
  )


def test_cell():
  c = f_cell()
  assert isinstance(c, list)
  assert torch.equal(
      torch.tensor(c),
      torch.tensor([[1, 2], [3, 4]])
  )


def test_if():
  assert f_if()[0, 0] == 2


def test_for():
  assert f_for()[0, 0] == 15


def test_while():
  assert f_while()[0, 0] == 1946738


test_cell()