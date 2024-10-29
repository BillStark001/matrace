from typing import List, Any
import functools


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
