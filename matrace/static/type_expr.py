from miss_hit_core.m_ast import *
from matrace.static.defs import VarType


def typeof_literal(node: Literal):
  if isinstance(node, Number_Literal):
    return VarType.NUMBER
  if isinstance(node, Char_Array_Literal):
    return VarType.CHAR_ARRAY
  if isinstance(node, String_Literal):
    return VarType.STRING
  assert False


def typeof_unary_opr(opr: str, elem: VarType) -> VarType:

  if elem == VarType.SLICE:
    elem = VarType.ROW_VEC

  if opr in ('ctranspose', "'", 'transpose', ".'"):
    if elem == VarType.NUMBER \
            or elem == VarType.BOOLEAN \
            or elem == VarType.MATRIX:
      return elem
    if elem == VarType.COL_VEC:
      return VarType.ROW_VEC
    if elem == VarType.ROW_VEC:
      return VarType.COL_VEC

  elif opr in ('uplus', '+', 'uminus', '-'):
    return elem

  elif opr in ('~', '!', 'not'):
    if elem == VarType.NUMBER:
      return VarType.BOOLEAN
    return elem

  assert False, 'TODO'


def typeof_binary_opr(opr: str, elem1: VarType, elem2: VarType) -> VarType:

  elem1_n = elem1 == VarType.NUMBER or elem1 == VarType.BOOLEAN
  elem2_n = elem2 == VarType.NUMBER or elem2 == VarType.BOOLEAN

  elem1_sl = elem1 == VarType.SLICE
  elem2_sl = elem2 == VarType.SLICE

  if elem1_sl:
    elem1 = VarType.ROW_VEC
  if elem2_sl:
    elem2 = VarType.ROW_VEC

  ret = None

  opr_is_power = opr in ('.^', 'power')
  opr_is_arithmetic = opr in (
      '+', 'plus', '-', 'minus',
      '.*', 'times', './', 'rdivide', '.\\', 'ldivide'
  ) or opr_is_power
  opr_is_logical = opr in (
      '<', 'lt', '>', 'gt', '<=', 'le', '>=', 'ge',
      '~=', 'ne', '==', 'eq',
      '&', '&&', 'and', '|', '||', 'or'
  )

  opr_is_mtimes = opr in ('*', 'mtimes')
  opr_is_mpower = opr in ('^', 'mpower')
  opr_is_matrix = opr_is_mtimes or opr_is_mpower \
      or opr in ('/', 'mrdivide', '\\', 'mldivide')

  if opr_is_arithmetic or opr_is_logical:
    if elem1_n and elem2_n:
      ret = VarType.NUMBER if opr_is_arithmetic else VarType.BOOLEAN
    if elem1 == elem2:
      ret = elem1
    if elem1 == VarType.MATRIX or elem2 == VarType.MATRIX:
      ret = VarType.MATRIX

    if elem1_n:
      ret = elem2
    if elem2_n:
      ret = elem1

    if elem1 == VarType.ROW_VEC and elem2 == VarType.COL_VEC:
      ret = VarType.MATRIX
    if elem1 == VarType.COL_VEC and elem2 == VarType.ROW_VEC:
      ret = VarType.MATRIX

  elif opr_is_matrix:
    if elem1_n and elem2_n:
      ret = VarType.NUMBER

    ret = VarType.MATRIX

  return ret
