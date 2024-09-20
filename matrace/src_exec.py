from typing import Any, List, Dict

import torch
import numpy as np

from miss_hit_core.m_ast import *
from miss_hit_core.m_ast import Node

from matrace.ast import FunctionASTVisitor
from matrace.opr_eval import eval_binary_opr, eval_subs_ref_arr, eval_unary_opr


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


def eval_literal(node: Literal):
  if isinstance(node, Number_Literal):
    v = node.t_value.value
    return int(v) if v.isdigit() else float(v)
  if isinstance(node, Char_Array_Literal):
    return str(node.t_string.value)
  if isinstance(node, String_Literal):
    return str(node.t_string.value)
  assert False


class CodeBlockExecutor(FunctionASTVisitor):

  def __init__(self):
    super().__init__()
    self.vars = {}

  def exec(self, node: Sequence_Of_Statements):
    return node.visit(None, self, 'Execution Root')
  
  def eval(self, node: Expression):
    node.visit(None, self, 'Evaluation Root')
    return self.last_on_visited

  def load_vars(self, **vars: Any):
    for k, v in vars.items():
      self.vars[k] = v

  def visit(self, node: Node, n_parent: Node | None, relation: str):
    assert is_simple_node(node)

    return super().visit(node, n_parent, relation)

  def subs_ref(self, path: List, root_obj=None):
    if root_obj is None:
      if isinstance(path[0], MATLAB_Token):
        ret = self.vars[path[0].value]
        path_lst = path[1:]
      else:
        assert len(path) == 1
        return path[0]
    else:
      ret = root_obj
      path_lst = path
    for p in path_lst:
      if isinstance(p, MATLAB_Token): # identifier
        ret = getattr(ret, p.value)
      elif isinstance(p, str): # string literal
        ret = p # TODO replace with standard evaluator
      elif isinstance(p, int):
        ret = eval_subs_ref_arr(ret, [p])
      elif isinstance(p, tuple):
        opr, path = p
        # path_obj = self.subs_ref(path)
        if opr == 'ds':
          ret = getattr(ret, self.subs_ref(path))
        else:
          path_referred = (
            self.subs_ref(x) if isinstance(x, list) else x 
            for x in path
          )
          if callable(ret) and opr == 'r':
            ret = ret(*path_referred)
          else:  # r, cr
            ret = eval_subs_ref_arr(ret, list(path_referred))
      else:
        assert False, 'TODO'
    return ret

  def subs_assign(self, path: List, obj: List):
    assert isinstance(path[0], MATLAB_Token)
    if len(path) < 2:
      self.vars[path[0].value] = obj
      return
    # at least 2
    ret = self.vars[path[0].value]
    final_path = path[-1]
    for p in path[1:-1]:
      if isinstance(p, MATLAB_Token):
        ret = getattr(ret, p.value)
      if isinstance(p, str):
        ret = p
      if isinstance(p, tuple):
        opr, path = p
        path_obj = self.subs_ref(path, ret)
        if opr == 'ds':
          ret = getattr(ret, path_obj)
        else:  # r, cr
          ret = ret[path_obj]
          
    if isinstance(final_path, MATLAB_Token):
      setattr(ret, final_path.value, obj)
    else:  # tuple
      opr, path = final_path
      path_obj = self.subs_ref(path, ret)
      if opr == 'ds':
        setattr(ret, path_obj, obj)
      else:  # r, cr
        eval_subs_ref_arr(ret, path_obj, obj)

  def eval_name(self, node: Name, relation: str, results: List, relations: List[str]):
    path = None
    if isinstance(node, Identifier):
      path = [node.t_ident]
    elif isinstance(node, Selection): # A.b
      rp, rf = results
      path = rp + rf
    elif isinstance(node, Dynamic_Selection): # A.(b)
      rp, rf = results
      # rf_obj = self.subs_ref(rf)
      path = rp + [('ds', rf)]
    elif isinstance(node, (Reference, Cell_Reference)): # A(b), A{b}
      rp, *rf = results
      # rf_obj = (self.subs_ref(x) for x in rf)
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
      return self.subs_ref(path)

    return path

  def eval_expression(self, node: Expression, params: List, relations: List[str]):
    if isinstance(node, Literal):
      return eval_literal(node)

    if isinstance(node, Unary_Operation):
      return eval_unary_opr(node.t_op.value, params[0])
    if isinstance(node, Binary_Operation):
      return eval_binary_opr(node.t_op.value, params[0], params[1])

    if isinstance(node, Reshape):
      return slice(None)
    if isinstance(node, Range_Expression):
      first = params[0]
      stride = params[1] if node.n_stride else 1
      last = params[-1]
      return slice(first, last + stride, stride)

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

