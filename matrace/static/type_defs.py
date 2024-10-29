from typing import Optional, List


class VarType():

  # oop operators
  
  def subs_static(self, target: str, assign: Optional['VarType']) -> Optional['VarType']:
    return None
  
  def subs_dynamic(self, target: 'VarType', assign: Optional['VarType']) -> Optional['VarType']:
    return None
  
  def subs_array(self, targets: List['VarType'], assign: Optional['VarType']) -> Optional['VarType']:
    return None
  
  def subs_cell(self, targets: List['VarType'], assign: Optional['VarType']) -> Optional['VarType']:
    return None

  # unary operators

  # matrix

  def ctranspose(self) -> Optional['VarType']:
    return None

  def transpose(self) -> Optional['VarType']:
    return None

  # arithmetic

  def uplus(self) -> Optional['VarType']:
    return None

  def uminus(self) -> Optional['VarType']:
    return None

  # logical

  def logical_not(self) -> Optional['VarType']:
    return None

  # binary operators

  # arithmetic

  def plus(self, b: 'VarType') -> Optional['VarType']:
    return None

  def minus(self, b: 'VarType') -> Optional['VarType']:
    return None

  def times(self, b: 'VarType') -> Optional['VarType']:
    return None

  def rdivide(self, b: 'VarType') -> Optional['VarType']:
    return None

  def ldivide(self, b: 'VarType') -> Optional['VarType']:
    return None

  def power(self, b: 'VarType') -> Optional['VarType']:
    return None

  # matrix

  def mtimes(self, b: 'VarType') -> Optional['VarType']:
    return None

  def mpower(self, b: 'VarType') -> Optional['VarType']:
    return None

  def mrdivide(self, b: 'VarType') -> Optional['VarType']:
    return None

  def mldivide(self, b: 'VarType') -> Optional['VarType']:
    return None

  # logical

  def lt(self, b: 'VarType') -> Optional['VarType']:
    return None

  def gt(self, b: 'VarType') -> Optional['VarType']:
    return None

  def le(self, b: 'VarType') -> Optional['VarType']:
    return None

  def ge(self, b: 'VarType') -> Optional['VarType']:
    return None

  def ne(self, b: 'VarType') -> Optional['VarType']:
    return None

  def eq(self, b: 'VarType') -> Optional['VarType']:
    return None

  def logical_and(self, b: 'VarType') -> Optional['VarType']:
    return None

  def logical_or(self, b: 'VarType') -> Optional['VarType']:
    return None
