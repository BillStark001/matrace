from typing import List, Any
import torch
import numpy as np

import functools


def eval_unary_opr(opr: str, elem: torch.Tensor) -> torch.Tensor:

  if opr in ('ctranspose', "'"):
    return torch.conj(elem).transpose(-2, -1)
  elif opr in ('transpose', ".'"):
    return torch.transpose(elem, -2, -1)
  elif opr in ('uplus', '+'):
    return elem
  elif opr in ('uminus', '-'):
    return -elem
  elif opr in ('~', '!', 'not'):
    return torch.logical_not(elem)
  assert False, 'TODO'


def eval_binary_opr(opr: str, elem1: torch.Tensor, elem2: torch.Tensor) -> torch.Tensor:

  if opr in ('+', 'plus'):
    return elem1 + elem2
  elif opr in ('-', 'minus'):
    return elem1 - elem2

  elif opr in ('.*', 'times'):
    return elem1 * elem2
  elif opr in ('*', 'mtimes'):
    return elem1 @ elem2
  elif opr in ('./', 'rdivide'):
    return elem1 / elem2
  elif opr in ('.\\', 'ldivide'):
    return elem2 / elem1
  elif opr in ('/', 'mrdivide'):
    return elem1 @ torch.inverse(elem2)
  elif opr in ('\\', 'mldivide'):
    return torch.inverse(elem2) @ elem1

  elif opr in ('.^', 'power'):
    return elem1 ** elem2
  elif opr in ('^', 'mpower'):
    assert elem2.numel() == 1
    elem2_int = elem2[0][0]
    # pylint: disable=E1102
    return elem1 ** elem2_int if elem1.numel() == 1 else \
        torch.linalg.matrix_power(elem1, elem2_int)

  elif opr in ('<', 'lt'):
    return elem1 < elem2
  elif opr in ('>', 'gt'):
    return elem1 > elem2
  elif opr in ('<=', 'le'):
    return elem1 <= elem2
  elif opr in ('>=', 'ge'):
    return elem1 >= elem2
  elif opr in ('~=', 'ne'):
    return elem1 != elem2
  elif opr in ('==', 'eq'):
    return elem2 == elem1

  # logical

  elif opr in ('&', '&&', 'and'):
    return torch.logical_and(elem1, elem2)
  elif opr in ('|', '||', 'or'):
    return torch.logical_or(elem1, elem2)

  assert False, 'TODO'

def slice_to_tensor(sub: slice, end_len=1):
  return torch.arange(
      sub.start if sub.start is not None else 0,
      sub.stop if sub.stop is not None else end_len,
      sub.step if sub.step is not None else 1,
      dtype=int)
