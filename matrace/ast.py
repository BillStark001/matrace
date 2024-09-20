from typing import List, Tuple, Dict, Generic, TypeVar

from miss_hit_core.m_ast import *
from miss_hit_core.m_ast import Node


T = TypeVar("T")

class FunctionASTVisitor(AST_Visitor, Generic[T]):
  
  def __init__(self):
    self.record_dict: Dict[int, List[Tuple[T, str]]] = {}
    self.last_on_visited: T = None
    
  def visit(self, node: Node, n_parent: Node | None, relation: str):
    self.record_dict[node.uid] = []
  
  def visit_end(self, node: Node, n_parent: Node | None, relation: str):
    record = self.record_dict[node.uid]
    del self.record_dict[node.uid]
    
    f_result = self.on_visited(node, relation, [x[0] for x in record], [x[1] for x in record])
    self.last_on_visited = f_result
    if n_parent is not None:
      self.record_dict[n_parent.uid].append((f_result, relation))
      
  def on_visited(self, node: Node, relation: str, results: List[T], relations: List[str]) -> T:
    pass
    