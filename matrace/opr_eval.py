from typing import List
import torch
import numpy as np


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
    return torch.linalg.matrix_power(elem1, elem2) # pylint: disable=E1102

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

def eval_subs_ref_arr(
  node: torch.Tensor, 
  subs: List[torch.Tensor | slice], 
  assign_target: torch.Tensor | None = None
):
  is_assign = assign_target is not None
  
  subs_parsed = []
  for sub in subs:
    sub_parsed = None
    if isinstance(sub, slice):
      sub_parsed = sub
    elif isinstance(sub, int):
      sub_parsed = sub - 1
    elif isinstance(sub, np.ndarray):
      sub_int = sub.astype(int) - 1 # to align python indices
      if sub_int.size == 1:
        sub_int = sub_int[0][0]
        sub_parsed = slice(sub_int, sub_int + 1)
      else: # sub_int is an index slice
        sub_parsed = sub_int
    else:
      raise TypeError(f'Not Implemented: subsref_arr - {type(sub)} / {sub}')
    
    subs_parsed.append(sub_parsed)
    
  if len(subs_parsed) == 1:
    if node.ndim > 2:
      dim_t = tuple(node.shape[:node.ndim - 2])
      nv = node.view((*dim_t, -1))
    else:
      nv = node.view(-1)
  else:
    nv = node
  
  ret = None
  if is_assign:
    nv[..., *subs_parsed] = assign_target
    ret = node
  else:
    ret = nv[..., *subs_parsed]
    if ret.ndim == 0:
      ret = ret.unsqueeze(0)
    if ret.ndim == 1:
      ret = ret.unsqueeze(1)
  return ret
  