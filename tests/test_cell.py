from matrace.stdlib.cells import concat_cells_col, concat_cells_row


def test_concat_cells_row_empty():
  assert concat_cells_row([]) == [[]]


def test_concat_cells_row_single():
  input_data = [[['a'], ['b']]]
  assert concat_cells_row(input_data) == [['a'], ['b']]


def test_concat_cells_row_basic():
  input_data = [
      [['a'], ['b']],
      [['c'], ['d']]
  ]
  expected = [['a', 'c'], ['b', 'd']]
  assert concat_cells_row(input_data) == expected


def test_concat_cells_row_complex():
  input_data = [
      [['a', 'b'], ['c', 'd']],
      [['e', 'f'], ['g', 'h']]
  ]
  expected = [['a', 'b', 'e', 'f'], ['c', 'd', 'g', 'h']]
  assert concat_cells_row(input_data) == expected


def test_concat_cells_col_empty():
  assert concat_cells_col([]) == [[]]


def test_concat_cells_col_single():
  input_data = [[['a'], ['b']]]
  assert concat_cells_col(input_data) == [['a'], ['b']]


def test_concat_cells_col_basic():
  input_data = [
      [['a'], ['b']],
      [['c'], ['d']]
  ]
  expected = [['a'], ['b'], ['c'], ['d']]
  assert concat_cells_col(input_data) == expected


def test_concat_cells_col_complex():
  input_data = [
      [['a', 'b'], ['c', 'd']],
      [['e', 'f'], ['g', 'h']]
  ]
  expected = [['a', 'b'], ['c', 'd'], ['e', 'f'], ['g', 'h']]
  assert concat_cells_col(input_data) == expected


def test_concat_cells_different_sizes():
  input_data = [
      [['a'], ['b']],
      [['c', 'd'], ['e', 'f']]
  ]
  expected = [['a', 'c', 'd'], ['b', 'e', 'f']]
  assert concat_cells_row(input_data) == expected
