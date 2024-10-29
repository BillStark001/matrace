from typing import TypeAlias, Any, List

import torch

from miss_hit_core.m_ast import Row, Row_List, Matrix_Expression, Cell_Expression

from matrace.std.cell_opr import concat_cells_row, concat_cells_col
from matrace.std.opr import slice_to_tensor

Evaluated: TypeAlias = Any


def eval_row_cat(items: List[Evaluated] | None) -> Evaluated:
  if not items:  # dummy row
    return None

  # this means it is not cell syntax {A}, but cell concatenation [A, B]
  is_cell_row = any(isinstance(x, list) for x in items)
  if is_cell_row:
    # it returns a cell array form
    return concat_cells_row(items), (True, False)

  # if is_mono_row, return 1d array or 1d list
  # else return 2d array
  is_mono_row = all(
      isinstance(x, (int, float, bool, slice))
      or (isinstance(x, torch.Tensor) and x.size(-2) == 1)
      for x in items
  )

  # handle slices
  for (i, item) in enumerate(items):
    if isinstance(item, slice):
      items[i] = slice_to_tensor(item)

  if is_mono_row:
    if len(items) == 1:
      i_v = items[0]
      if isinstance(i_v, torch.Tensor):
        is_mono_row = False
        vals = i_v
      else:
        vals = [i_v]
    else:
      vals_lst = []
      for i_v in items:
        if isinstance(i_v, torch.Tensor):
          vals_lst.extend(i_v if i_v.dim() == 1 else i_v[..., 0, :])
        else:
          vals_lst.append(i_v)
      vals = vals_lst

  else:
    # all items must be tensors
    # otherwise it does not make sense, so torch will throw errors
    if len(items) == 1:
      vals = items[0]  # just return the 2D tensor
    # else there are multiple items, concatenation needed
    else:
      vals: torch.Tensor = torch.cat([x[0] for x in items], dim=-1)

  return vals, (is_cell_row, is_mono_row)


def eval_col_cat(rows_raw: List[List[Evaluated]], is_cell=False) -> Evaluated:

  rows = [eval_row_cat(row) for row in rows_raw]

  if len(rows) == 0:
    if is_cell:
      return []
    return torch.tensor([[]], float)

  if len(rows) == 1:
    row_val, (c_cr, c_mr) = rows[0]
    if is_cell or c_cr:  # row_val instanceof cell array
      return row_val
    elif c_mr:  # row_val is 1-d
      return torch.tensor([row_val])
    # else it is already a tensor
    return row_val
  # else
  
  if is_cell:
    concatenated_rows = []
    for row, _ in rows:
      concatenated_rows.append(concat_cells_row(row))
    return concat_cells_col(concatenated_rows)
  
  rows_elems = [x[0] for x in rows]
  any_cell_rows = any(x[1][0] for x in rows)
  any_mat_rows = any(not x[1][0] for x in rows)
  all_mono_rows = all(x[1][1] for x in rows)

  if any_cell_rows and any_mat_rows:
    raise Exception('Unsupported column concatenation')
  # otherwise it must be all cell rows or all mat rows

  if any_cell_rows:
    row_val = concat_cells_col(rows_elems)
    return row_val
  # else, it must be all_mat_rows
  elif all_mono_rows:
    row_val = torch.tensor(rows_elems, dtype=float)
    return row_val

  # else just cat
  row_val = rows_elems
  for i, (_, mono_row) in enumerate(x[1] for x in rows):
    if mono_row:
      row_val[i] = [row_val[i]]
  row_val = torch.cat(row_val, dim=-2)
  return row_val
