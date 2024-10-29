from typing import Any, List, Dict, Optional, Tuple

import torch
import numpy as np

from miss_hit_core.m_ast import *
from miss_hit_core.m_ast import Node

from matrace.ast import FunctionASTVisitor
from matrace.static.defs import SymbolRecord, LexicalScope, VarType

from matrace.static.type_expr import typeof_unary_opr, typeof_binary_opr, typeof_literal
from matrace.utils.nested_dict import NestedDict


def is_simple_node(node: Node):
  return isinstance(node, (
      Simple_Assignment_Statement,
      Compound_Assignment_Statement,
      Naked_Expression_Statement,
      Sequence_Of_Statements,
      Expression,
      Row_List,
      Row,
  ))


def get_next_scope(
  node: Node, 
  parent: Node | None,
  relation: str, 
  scope: LexicalScope = LexicalScope.DEFAULT
) -> LexicalScope | None:
  if isinstance(node, Matrix_Expression):
    return LexicalScope.ARR_EXPR
  if isinstance(node, Cell_Expression):
    return LexicalScope.CELL_EXPR

  if isinstance(node, Row_List) and scope == LexicalScope.ARR_EXPR:
    return LexicalScope.VERT_CAT
  if isinstance(node, Row) and scope == LexicalScope.VERT_CAT:
    return LexicalScope.HORZ_CAT

  if isinstance(node, Reference):
    return LexicalScope.ARR_REF
  if isinstance(node, Cell_Reference):
    return LexicalScope.CELL_REF
  
  if isinstance(parent, Selection) and relation == "Field":
    return LexicalScope.SUBS_REF_FIELD
  
  if isinstance(node, (Simple_Assignment_Statement, Compound_Assignment_Statement)) \
    and relation == "LHS":
    return LexicalScope.SUBS_ASSIGN

  return None # the next scope is not needed

COMPOUND_ASGN_RETURN = '__COMPOUND_ASGN_RETURN'

class CodeAnalyzer(FunctionASTVisitor):

  def __init__(self):
    super().__init__()
    self.root: NestedDict[str, SymbolRecord] = NestedDict()
    self.current = self.root
    self.records_by_symbol: Dict[int, NestedDict[str, SymbolRecord]] = {}
    self.scopes: List[Tuple[int, LexicalScope]] = []

  @property
  def scope(self):
    if not self.scopes:
      return LexicalScope.DEFAULT
    return self.scopes[-1][1]
  
  @property
  def scope_uid(self):
    if not self.scopes:
      return -1
    return self.scopes[-1][0]


  def typeof(self, name: str):
    if name in self.current:
      return self.current[name].type
    return None



  def record_create(self, node: Node, parent: Optional[int] = None):
    current = self.records_by_symbol.get(parent, None)
    if current is None:
      current = self.current

    r = self.current.create_child()
    self.records_by_symbol[node.uid] = r
    self.current = r

    return r

  def analyze(self, node: Sequence_Of_Statements):
    return node.visit(None, self, 'Execution Root')

  def visit(self, node: Node, n_parent: Node | None, relation: str):
    super().visit(node, n_parent, relation)
    assert is_simple_node(node)
    # evolve lexical scope
    next_scope = get_next_scope(node, n_parent, relation, self.scope)
    if next_scope is not None:
      self.scopes.append((node.uid, next_scope))
  
  def visit_end(self, node: Node, n_parent: Node | None, relation: str):
    # revert lexical scope
    if self.scope_uid == node.uid:
      self.scopes.pop()
    
    super().visit_end(node, n_parent, relation)
  

  def eval_name(self, node: Name, relation: str, results: List, relations: List[str]):
    path = None
    if isinstance(node, Identifier):
      return self.typeof(node.t_ident.value) \
        if self.scope != LexicalScope.SUBS else VarType.NUMBER
    if isinstance(node, Selection):  # A.b
      sel_parent, *_ = results
      sel_name = node.n_field.t_ident.value
      # TODO return sel_parent.subs_static(sel_name)
    if isinstance(node, Dynamic_Selection):  # A.(b)
      sel_parent, sel_name = results
      # return sel_parent.subs_dynamic(sel_name)
    elif isinstance(node, (Reference, Cell_Reference)):  # A(b), A{b}
      rp, *rf = results
      # rf_obj = (self.subsref(x) for x in rf)
      path = rp + [('r' if isinstance(node, Reference) else 'cr', rf)]
    else:
      assert False, 'TODO'

    out_layer = (not isinstance(node.n_parent, Name) \
                 # or isinstance(node.n_parent, (Dynamic_Selection, Reference, Cell_Reference))
                 ) \
        and not (isinstance(node.n_parent, (
            Simple_Assignment_Statement,
            Compound_Assignment_Statement)) and relation == 'LHS')
    if out_layer:
      return self.subsref(path)

    return path

  def eval_expression(self, node: Expression, params: List[VarType], relations: List[str]) -> VarType:
    if isinstance(node, Literal):
      return typeof_literal(node)

    if isinstance(node, Unary_Operation):
      if isinstance(node.n_expr, Identifier) and params[0] == VarType.SLICE:
        self.current[node.n_expr.t_ident.value].used_as_array = True
      return typeof_unary_opr(node.t_op.value, params[0])
    
    if isinstance(node, Binary_Operation):
      if isinstance(node.n_lhs, Identifier) and params[0] == VarType.SLICE:
        self.current[node.n_lhs.t_ident.value].used_as_array = True
      if isinstance(node.n_rhs, Identifier) and params[0] == VarType.SLICE:
        self.current[node.n_rhs.t_ident.value].used_as_array = True
      return typeof_binary_opr(node.t_op.value, params[0], params[1])

    if isinstance(node, Reshape):
      return VarType.SLICE
    if isinstance(node, Range_Expression):
      return VarType.SLICE

    if isinstance(node, (Matrix_Expression, Cell_Expression)):
      return params[0]

    assert False, 'TODO'

  def handle_rows(self, node: Row | Row_List, params: List):
    if isinstance(node, Row):
      if len(params) == 0:
        return None
      if node.n_parent is not None and isinstance(node.n_parent.n_parent, Matrix_Expression):
        return torch.cat(params, dim=-1) if len(params) > 1 else params[0]
      return params
    # else it is a row list
    params_f = [x for x in params if x is not None]
    if isinstance(node.n_parent, Matrix_Expression):
      return torch.cat(params_f, dim=-2)
    return params_f

  def on_visited(self, node: Node, relation: str, results: List, relations: List[str]) -> Any:
    if isinstance(node, (Name, Function_Call)):
      return self.eval_name(node, relation, results, relations)
    if isinstance(node, (Row, Row_List)):
      return self.handle_rows(node, results)
    if isinstance(node, Expression):
      return self.eval_expression(node, results, relations)

    if isinstance(node, (Naked_Expression_Statement, Sequence_Of_Statements)):
      # the expression is already evaluated
      return None

    if isinstance(node, (Simple_Assignment_Statement, Compound_Assignment_Statement)):
      r_lhs = results[:-1]
      r_expr = results[-1]
      if isinstance(node.n_rhs, Literal):
        r_expr = np.array([[r_expr]])  # so that all vars are matrices

      if isinstance(node, Simple_Assignment_Statement):
        r_expr = [r_expr]
      for i, n in enumerate(r_lhs):
        self.subs_assign(n, r_expr[i])
      return None

    assert False, 'TODO'
