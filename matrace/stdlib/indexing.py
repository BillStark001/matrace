from typing import List, Any, Tuple
import torch
import numpy as np

from matrace.stdlib.operators import slice_to_tensor


def parse_subsref_arr_slice(sub, is_mono=False):

  if isinstance(sub, slice):
    # A = a:b:c
    # end operator is handled otherwise
    return slice(
        sub.start - 1 if sub.start is not None else None,
        sub.stop - 1 if sub.stop is not None else None,
        sub.step if sub.step is not None else None,
    )
  if isinstance(sub, (int, float)):
    sub = int(sub)
    # in order to retain the shape
    return slice(sub - 1, sub, 1)

  if isinstance(sub, torch.Tensor):
    # variable defined
    sub_int = sub.int() - 1
    if len(sub.shape) == 0:
      sub_int = sub_int.view((1))
    elif len(sub.shape) > 1 and not is_mono:
      # flatten the tensor if more than 1 tensors are passed
      # otherwise the shape needs to be retained
      sub_int = sub_int.transpose(-1, -2).contiguous().view((-1))
    return sub_int

  assert False, 'TODO'


def gen_torch_slice_by_subsref_slice(
    subs_parsed: List[slice | np.ndarray | torch.Tensor | int],
    size: Tuple[int, int],
):

  mono_colon = False

  if len(subs_parsed) == 1:
    sub = subs_parsed[0]
    if isinstance(sub, slice):
      mono_colon = sub.start is None and sub.stop is None and sub.step is None
      sub = slice_to_tensor(sub, size[-2] * size[-1])
    if isinstance(sub, np.ndarray):
      sub = torch.tensor(sub, dtype=int)

    # from this point, sub is a tensor
    # parse row and col
    row_cnt = size[-2]
    if sub.dim() < 2:
      # reshape it so that the result becomes a row vector
      reshape_shape = (sub.numel(), 1) \
          if mono_colon else (1, sub.numel())
      sub = sub.reshape(reshape_shape)
    # else retain the shape
    sub_col = sub // row_cnt
    sub_row = sub - sub_col * row_cnt

  elif len(subs_parsed) == 2:
    sub0, sub1 = subs_parsed
    sub0 = slice_to_tensor(sub0, size[0]) if isinstance(sub0, slice) else sub0
    sub1 = slice_to_tensor(sub1, size[1]) if isinstance(sub1, slice) else sub1
    xx, yy = torch.meshgrid(sub0, sub1, indexing='ij')
    sub_col = yy
    sub_row = xx

  else:
    assert False, 'TODO'

  return sub_row, sub_col


def commit_subsref_or_subsasgn_arr(
    node: torch.Tensor | List[List[Any]],
    subs_parsed: List[slice | np.ndarray | torch.Tensor | int],
    assign_rhs: torch.Tensor | None = None,
    copy_required: bool = False,
):

  if not subs_parsed:
    assert assign_rhs is None, 'WTF'
    return node

  sub_row, sub_col = gen_torch_slice_by_subsref_slice(
      subs_parsed,
      node.shape if isinstance(node, torch.Tensor) \
        else (len(node), 1 if not node else len(node[0])),
  )

  if assign_rhs is not None:
    if isinstance(node, torch.Tensor):
      if copy_required:
        node = node.clone()
      node[sub_row, sub_col] = assign_rhs.transpose(-2, -1).flatten()
      return node
    # else it is a cell array
    if copy_required:
      node = [[*x] for x in node]
    (*_, n_rows, n_cols) = sub_row.shape
    for i_row in range(n_rows):
      for i_col in range(n_cols):
        node[sub_row[i_row, i_col]][sub_col[i_row, i_col]] = assign_rhs[i_row][i_col]
    return node

  # else assign_rhs is none
  if isinstance(node, torch.Tensor):
    return node[sub_row, sub_col]
  # else it is a cell array
  (*_, n_rows, n_cols) = sub_row.shape
  ret = []
  for i_row in range(n_rows):
    ret_row = []
    for i_col in range(n_cols):
      ret_row.append(node[sub_row[i_row, i_col]][sub_col[i_row, i_col]])
    ret.append(ret_row)
  return ret


def eval_subsref_arr(
    node: torch.Tensor | List[List[Any]],
    subs: List[torch.Tensor | slice],
    assign_target: torch.Tensor | None = None
):
  subs_parsed = [
      parse_subsref_arr_slice(sub, is_mono=len(subs) < 2)
      for sub in subs
  ]

  return commit_subsref_or_subsasgn_arr(node, subs_parsed, assign_target)
