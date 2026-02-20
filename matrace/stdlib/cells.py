from typing import List, Any
import functools

import torch


def _cell_idx_to_int(v) -> int:
  """Convert a MATLAB index value (tensor or scalar) to a Python int."""
  if isinstance(v, torch.Tensor):
    return int(v.item())
  return int(v)


class CellExpansion:
  """Represents the result of ``C{:}`` — all cell elements expanded as a
  comma-separated list so that matrix context can concatenate them.

  Column-major order is used, consistent with MATLAB linear indexing.
  """

  def __init__(self, elements: List[Any]):
    self.elements = elements


def eval_subsref_cell(
    cell: List[List[Any]],
    indices: List[Any],
) -> Any:
  """MATLAB-style cell element access.

  Cell arrays are stored as ``List[List[Any]]`` (row-major, 0-based
  internally).  MATLAB indices are 1-based.

  Supports:
  * Colon ``C{:}``            — returns a :class:`CellExpansion` of all
    elements in column-major order, suitable for use inside ``[...]``.
  * Linear indexing ``C{k}``  — 1-based, column-major.
  * Two-index ``C{i, j}``     — 1-based row/column.
  """
  if len(indices) == 1:
    idx = indices[0]
    # C{:} — expand all elements in column-major order
    if isinstance(idx, slice) and idx.start is None and idx.stop is None:
      n_rows = len(cell)
      n_cols = len(cell[0]) if cell else 0
      return CellExpansion(
          [cell[r][c] for c in range(n_cols) for r in range(n_rows)]
      )
    k = _cell_idx_to_int(idx) - 1  # 0-based
    n_rows = len(cell)
    row = k % n_rows
    col = k // n_rows
    return cell[row][col]
  if len(indices) == 2:
    row = _cell_idx_to_int(indices[0]) - 1
    col = _cell_idx_to_int(indices[1]) - 1
    return cell[row][col]
  raise NotImplementedError(
      f'Cell indexing with {len(indices)} subscripts is not supported.'
  )


def subsasgn_cell(
    cell: List[List[Any]],
    indices: List[Any],
    value: Any,
) -> None:
  """In-place cell element assignment (MATLAB 1-based indices)."""
  if len(indices) == 1:
    k = _cell_idx_to_int(indices[0]) - 1
    n_rows = len(cell)
    row = k % n_rows
    col = k // n_rows
    cell[row][col] = value
    return
  if len(indices) == 2:
    row = _cell_idx_to_int(indices[0]) - 1
    col = _cell_idx_to_int(indices[1]) - 1
    cell[row][col] = value
    return
  raise NotImplementedError(
      f'Cell assignment with {len(indices)} subscripts is not supported.'
  )

def concat_cells_row(items: List[List[List[Any]] | Any]) -> List[List[Any]]:
  if not items:
    return [[]]
  if len(items) == 1:
    return items[0]
  row_number = len(items[0]) if isinstance(items[0], list) else 1
  # sanity check
  for item in items:
    item_row_number = len(item) if isinstance(item, list) else 1
    assert row_number == item_row_number

  new_cell = []
  for row_index in range(row_number):
    new_row = []
    for item in items:
      if isinstance(item, list):
        new_row += item[row_index]
      else:
        new_row.append(item)
    new_cell.append(new_row)
  return new_cell


def concat_cells_col(items: List[List[List[Any]]]) -> List[List[Any]]:
  if not items:
    return [[]]
  if len(items) == 1:
    return items[0]
  return functools.reduce(lambda x, y: x + y, items, [])
