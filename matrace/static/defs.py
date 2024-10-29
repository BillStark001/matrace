from enum import Enum
from dataclasses import dataclass


class VarType(Enum):

  NUMBER = 0
  ROW_VEC = 1
  COL_VEC = 2
  MATRIX = 3

  BOOLEAN = 5

  ROW_CELL = 10
  COL_CELL = 11
  MAT_CELL = 12

  STRING = 20
  CHAR_ARRAY = 21

  SLICE = 25

  STRUCT = 30
  CLASS = 31


class LexicalScope(Enum):

  DEFAULT = 0

  LOOP = 5
  CONDITION = 6

  CELL_EXPR = 10
  ARR_EXPR = 11
  
  HORZ_CAT = 12
  VERT_CAT = 13

  CELL_REF = 20
  ARR_REF = 21
  
  SUBS = 30
  SUBS_ASSIGN = 31
  SUBS_REF_FIELD = 32


@dataclass
class SymbolRecord():

  id: int

  type: VarType = VarType.MATRIX

  is_row_vec: bool = False
  is_col_vec: bool = False
  is_mat: bool = False

  reference_count: int = 0
  needs_copy: bool = False
  needs_expand: bool = False

  used_as_slice: bool = False
  used_as_array: bool = False
  used_as_range: bool = False

  is_row_list: bool = False
  is_row_array: bool = False
