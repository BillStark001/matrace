from typing import Optional, List, Union, Protocol, Any, Tuple, Dict, Literal as Literal2, Generic, TypeVar

import dataclasses

from miss_hit_core.m_ast import *
from miss_hit_core.m_ast import Node

from matrace.ast import FunctionASTVisitor
from matrace.src_exec import eval_literal


@dataclasses.dataclass
class DynamicIdentifier:
  value: str | int
  type: Literal2['obj', 'arr', 'list']

  def __hash__(self) -> int:
    return hash(self.value) | hash(self.type)

  def __eq__(self, value: object) -> bool:
    if not isinstance(value, DynamicIdentifier):
      return False
    return self.value == value.value and self.type == value.type


_DI_STR = '%%%%$$$$####DI'
DI_OBJ = DynamicIdentifier(_DI_STR, 'obj')
DI_ARRAY = DynamicIdentifier(_DI_STR, 'arr')
DI_LIST = DynamicIdentifier(_DI_STR, 'list')


def get_general_di(di: DynamicIdentifier):
  if di.type == 'arr':
    return DI_ARRAY
  if di.type == 'list':
    return DI_LIST
  return DI_OBJ


def generalize(di: str | DynamicIdentifier):
  if isinstance(di, DynamicIdentifier):
    child = get_general_di(di)
  else:
    child = di
  return child


class RelationNode:

  def __init__(
      self,
      current: str | DynamicIdentifier,
  ):
    self.current = current
    self.children: Dict[str | DynamicIdentifier, RelationNode] = {}
    self.as_reference = False

  def ensure(self, id: str | DynamicIdentifier):
    if not id in self.children:
      self.children[id] = RelationNode(id)

  def add(self, path: List[str | DynamicIdentifier]) -> 'RelationNode':
    if not path:
      return self
    p0 = path[0]
    p1 = path[1:]
    child = generalize(p0)
    self.ensure(p0)
    self.ensure(child)
    return self.children[child].add(p1)

  def add_as(self, path: List[str | DynamicIdentifier], ref: List[str | DynamicIdentifier]):
    n = self.add(path)
    r = self.add(ref)
    n.as_reference = True
    merge_relation_node(n, r)
    return n
    
  def export(self, dynamic_key='DYNAMIC_IDENTIFIER_'):
    export_target = {}
    for child, child_node in self.children.items():
      child_key = child
      if isinstance(child, DynamicIdentifier):
        child_key = dynamic_key + child.type
      export_target[child_key] = child_node.export()
    return export_target



def merge_relation_node(src: RelationNode, dst: RelationNode):
  for c in src.children:
    if c in dst.children:
      merge_relation_node(src.children[c], dst.children[c])
    dst.children[c] = src.children[c]
  src.children = dst.children


class RelationRecorder(FunctionASTVisitor):

  def __init__(self):
    super().__init__()
    self.root_node = RelationNode('')

  def on_visited(self, node: Node, relation: str, results: List[None], relations: List[str]) -> None:
    if isinstance(node, Identifier):
      return [node.t_ident.value]
    if isinstance(node, Literal):
      return eval_literal(node)
    if isinstance(node, (Reshape, Range_Expression)):
      return slice(None)
    # TODO Range_Expression, Matrix_Expression

    if isinstance(node, Name):
      ret = []
      if isinstance(node, Selection):
        rp, rf = results
        ret = rp + rf
      elif isinstance(node, Dynamic_Selection):
        rp = results[0]
        ret = rp + [DI_OBJ]
      elif isinstance(node, Reference):
        rp = results[0]  # n_ident
        ret = rp + [DI_ARRAY]
      elif isinstance(node, Cell_Reference):
        rp = results[0]  # n_ident
        ret = rp + [DI_LIST]

      if not isinstance(node.n_parent, Name):
        self.root_node.add(ret)

      return ret

    if isinstance(node, Simple_Assignment_Statement):
      r_lhs, r_rhs = results
      if isinstance(r_lhs, list) and isinstance(r_rhs, list):
        self.root_node.add_as(r_lhs, r_rhs)
      pass
    if isinstance(node, Compound_Assignment_Statement):
      r_lhs = results[:-1]
      r_rhs = results[-1]
      for r_lhs_v in r_lhs:
        if isinstance(r_lhs_v, list) and isinstance(r_rhs, list):
          self.root_node.add_as(r_lhs_v, r_rhs)
        pass
    
  def export(self):
    return self.root_node.export()


def analyze_relation(node: Node):
  rel = RelationRecorder()
  node.visit(None, rel, 'Root')
  return rel.export()