from typing import Any, List, Dict, cast, Generator

import dataclasses
import torch

from miss_hit_core.m_ast import *

from matrace.mh.cfg import CFG, CFGNode, CFGType, generate_cfg
from matrace.exec_flow import CodeExecutor, Evaluated
from matrace.utils import ContextManager

STOP_ITR = -1


def get_gen(gen):
  try:
    return next(gen), True
  except StopIteration:
    return None, False


@dataclasses.dataclass
class ForLoopContext:
  generator: Generator[Any, None, None]
  identifier: str

  has_next: bool = False

  def next(self):
    return get_gen(self.generator)


default_for = ForLoopContext(generator=(x for x in []), identifier='')
NO_OPR_TYPES = {
    CFGType.GLOBAL_ENTRY,
    CFGType.GLOBAL_EXIT,
    CFGType.IF_ENTRY,
    CFGType.IF_EXIT,
    CFGType.IF_ACTION_ENTRY,
    CFGType.FOR_CONTINUE,

    CFGType.WHILE_ENTRY,
    CFGType.WHILE_CONTINUE,
    CFGType.WHILE_EXIT,
}
# TODO add all types


class CodeControlExecutor(CodeExecutor):

  def __init__(self):
    super().__init__()
    self.for_loop = ContextManager(default_for)

  def eval(
    self, node: Expression | str, 
    *args, **kwargs,
  ) -> Evaluated:
    if isinstance(node, str):
      if node == 'FOR_HAS_NEXT':
        return self.for_loop.current.has_next
      assert False, 'TODO'
    return super().eval(node, *args, **kwargs)

  def exec_node(
      self,
      node: CFGNode,
  ):
    t = node.type

    if t == CFGType.SEQUENCE:
      self.exec(node.stmt_list)

    elif t == CFGType.FOR_INIT:
      stmt = cast(General_For_Statement, node.stmt_list)
      iterator = self.eval(stmt.n_expr)
      if isinstance(iterator, torch.Tensor):
        iterator = iterator.view(-1)

      if isinstance(iterator, slice):
        iterator = range(iterator.start, iterator.stop, iterator.step or 1)
      context = ForLoopContext(
          generator=(e for e in iterator),
          identifier=stmt.n_ident.t_ident.value,
      )
      self.for_loop.push(context)

    elif t == CFGType.FOR_ENTRY:
      _for = self.for_loop.current
      element, cont = _for.next()
      _for.has_next = cont
      if cont:
        self.load_vars(**{_for.identifier: element})

    elif t == CFGType.FOR_EXIT:
      self.for_loop.pop()

    elif t in NO_OPR_TYPES:
      pass

    else:
      assert False, 'TODO'

  def get_next_node(
      self,
      node_id: int,
      cfg: CFG,
  ) -> int:
    opts = cfg.next_node(node_id)
    for opt_id, cond in opts:  # evaluate all edges by precedence
      if cond is None:  # unconditional jump
        return opt_id
      # else cond is not None, evaluate it
      val = self.eval(cond)
      cond_eval = False
      if isinstance(val, torch.Tensor):
        cond_eval = torch.all(val)
      elif isinstance(val, bool):
        cond_eval = val
      else:
        cond_eval = not not val
      if cond_eval:
        return opt_id
    return STOP_ITR


def exec_func(
    src: Function_Definition,
    params: List | None = None,
    scope: Dict | None = None,
):
  ex = CodeControlExecutor()

  # load global scope
  if scope is not None:
    ex.load_vars(**scope)

  # load parameters
  params_dict = {}
  for i, n in enumerate(src.n_sig.l_inputs):
    nv: str = n.t_ident.value
    params_dict[nv] = params[i]
  ex.load_vars(**params_dict)

  cfg = generate_cfg(src.n_body)
  cur_node_id = cfg.entry_id

  # CFG
  while cur_node_id != cfg.exit_id:
    cur_node = cfg.node(cur_node_id)
    ex.exec_node(cur_node)
    next_node = ex.get_next_node(cur_node_id, cfg)
    if next_node == STOP_ITR:
      assert False, 'Should not happen'
    cur_node_id = next_node

  # gather and return outputs
  ret_value = None
  
  if len(src.n_sig.l_outputs) != 0:
    ret = []
    for n in src.n_sig.l_outputs:
      nv: str = n.t_ident.value
      ret.append(ex.vars[nv])
    ret_value = ret[0] if len(src.n_sig.l_outputs) == 1 else ret

  return ret_value
