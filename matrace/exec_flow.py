from dataclasses import dataclass
from typing import Any, List, Dict, TypeAlias, Tuple


import torch
import numpy as np

from miss_hit_core.m_ast import *
from miss_hit_core.m_ast import Node

from matrace.std.mat_subs import eval_subsref_arr
from matrace.std.mat_opr import eval_col_cat
from matrace.std.cell_opr import concat_cells_col, concat_cells_row
from matrace.std.opr import eval_binary_opr, eval_unary_opr
from matrace.utils.context import ContextManager


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


Evaluated: TypeAlias = Any


# func call


def func_call(obj: Evaluated, target: Evaluated) -> Evaluated:
  return obj(*target)

# subsref


def subsref_obj(obj: Evaluated, target: str | Evaluated, is_static=False) -> Evaluated:
  return getattr(obj, target)


# TODO this is not correct
def subsref_list(obj: Evaluated, target: Evaluated) -> Evaluated:
  return obj[*target]


def expr_literal(node: Literal, strict_matrix=True) -> Evaluated:
  ret = None
  if isinstance(node, Number_Literal):
    v = node.t_value.value
    ret = int(v) if v.isdigit() else float(v)
    if strict_matrix:
      ret = torch.tensor([[ret]], dtype=float)
  elif isinstance(node, Char_Array_Literal):
    ret = str(node.t_string.value)
  elif isinstance(node, String_Literal):
    ret = str(node.t_string.value)
  else:
    assert False, 'TODO'
  return ret


# matrices


@dataclass
class MatrixContext:
  shape: Tuple[int, ...] = (1, 1)

  def shape_of(self, x: int):
    # x: 0-based
    y = 1
    for z in self.shape[x:]:
      y *= z
    return y


class CodeExecutor:

  def __init__(self):
    self.vars = {}
    self.mat_ctx = ContextManager(default=MatrixContext((1, 1)))

  def load_vars(self, **vars_in: Any):
    for k, v in vars_in.items():
      self.vars[k] = v

  def exec(self, node: Sequence_Of_Statements):

    for stmt in node.l_statements:
      if isinstance(stmt, Naked_Expression_Statement):
        self.eval(stmt.n_expr)
      elif isinstance(stmt, (Simple_Assignment_Statement, Compound_Assignment_Statement)):
        self.subsasgn(stmt)

  def subsasgn(self, node: Simple_Assignment_Statement | Compound_Assignment_Statement):
    is_simple = isinstance(node, Simple_Assignment_Statement)
    rhs = self.eval(node.n_rhs)
    lhs_lst: List[Name] = [node.n_lhs] if is_simple else node.l_lhs
    rhs_lst = [rhs] if is_simple else list(rhs)

    # commit assignments
    for i in range(len(lhs_lst)):
      lhs_i = lhs_lst[i]
      rhs_i = rhs_lst[i]

      if isinstance(lhs_i, Identifier):
        self.vars[lhs_i.t_ident.value] = rhs_i  # lhs_i

      elif isinstance(lhs_i, Selection):
        ev = self.eval(lhs_i.n_prefix)
        target = lhs_i.n_field.t_ident.value
        setattr(ev, target, rhs_i)

      elif isinstance(lhs_i, Dynamic_Selection):
        ev = self.eval(lhs_i.n_prefix)
        tv = self.eval(lhs_i.n_field)
        setattr(ev, tv, rhs_i)

      elif isinstance(lhs_i, (Cell_Reference, Reference)):
        is_cell = isinstance(lhs_i, Cell_Reference)
        args_object = [self.eval(x) for x in lhs_i.l_args]
        lhs_value = self.eval(lhs_i.n_ident)

        if is_cell:
          # TODO this is not correct
          lhs_value[*args_object] = rhs_i
        else:
          # create a temporary variable
          # evaluate the subsref at last
          eval_subsref_arr(lhs_value, args_object, rhs_i)

      else:
        assert False, 'WTF'

  def eval(
      self,
      node: Expression,
      strict_matrix=True,
      index_of_slice=-1,
      last_slice=False,
  ) -> Evaluated:

    # literal and oprs
    assert isinstance(node, Expression), str(node)

    if isinstance(node, Literal):
      return expr_literal(node, strict_matrix=strict_matrix)

    if isinstance(node, Unary_Operation):
      elem = self.eval(node.n_expr)
      return eval_unary_opr(node.t_op.value, elem)

    if isinstance(node, Binary_Operation):
      elem1 = self.eval(node.n_lhs)
      elem2 = self.eval(node.n_rhs)
      return eval_binary_opr(node.t_op.value, elem1, elem2)

    if isinstance(node, Reshape):
      return slice(None)

    if isinstance(node, Range_Expression):
      # evaluate the range operator as-is, from [fv, lv] to [fv, lv+1)
      fv = self.eval(node.n_first, strict_matrix=False)
      sv = self.eval(node.n_stride, strict_matrix=False) \
          if node.n_stride else None
      lv = self.eval(node.n_last, strict_matrix=False)
      return slice(fv, lv + 1, sv)

    # identifier

    if isinstance(node, Identifier):
      # handle the end operator
      # this is a reserved keyword, so it must be in matrix context
      if node.t_ident.value == 'end':
        return self.mat_ctx.current.shape_of(index_of_slice) \
            if last_slice else self.mat_ctx.current.shape[index_of_slice]

      # references should never reach here
      value = self.vars[node.t_ident.value]
      return value

    if isinstance(node, Selection):
      obj = self.eval(node.n_prefix)
      target = node.n_field.t_ident.value
      return subsref_obj(obj, target, True)

    if isinstance(node, Dynamic_Selection):
      obj = self.eval(node.n_prefix)
      target = self.eval(node.n_field)
      return subsref_obj(obj, target)

    if isinstance(node, (Cell_Reference, Reference)):
      is_cell = isinstance(node, Cell_Reference)
      lhs = self.eval(node.n_ident)
      is_call = callable(lhs)

      if not is_cell and not is_call:
        # inject the end operator, etc.
        self.mat_ctx.push(MatrixContext(tuple(lhs.shape)))

      args_object = [self.eval(x, index_of_slice=i)
                     for (i, x) in enumerate(node.l_args)]

      if not is_cell and not is_call:
        self.mat_ctx.pop()

      # TODO strict matrix adaption

      return (subsref_list if is_cell else (
          func_call if is_call else eval_subsref_arr
      ))(
          # this must be a name, i.e. identifier, reference, ...
          lhs,
          args_object
      )

    if isinstance(node, (Matrix_Expression, Cell_Expression)):
      return self.eval_cols(node)

    assert False, 'TODO: ' + node.__class__.__name__

  def eval_cols(self, node: Matrix_Expression | Cell_Expression) -> Evaluated:
    is_cell = isinstance(node, Cell_Expression)

    # evaluate all items
    row_items = []
    for row_node in node.n_content.l_items:
      if not row_node.l_items:
        continue  # dummy row
      items = [
          self.eval(x, strict_matrix=False)
          for x in row_node.l_items
      ]
      row_items.append(items)

    return eval_col_cat(row_items, is_cell)
