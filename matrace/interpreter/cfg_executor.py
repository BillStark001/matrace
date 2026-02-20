from typing import Any, List, Dict, cast, Generator

import dataclasses
import torch

from miss_hit_core.m_ast import *

from matrace.ir.cfg import CFG, CFGNode, CFGType, generate_cfg
from matrace.interpreter.executor import CodeExecutor, Evaluated
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

    # Switch: action routing is handled in get_next_node; exec is a no-op
    CFGType.SWITCH_ACTION_ENTRY,
    CFGType.SWITCH_EXIT,

    # SPMD: executed serially (no parallel support)
    CFGType.SPMD_ENTRY,
    CFGType.SPMD_EXIT,

    # Try/catch: exceptions are not caught; bodies execute inline
    CFGType.TRY_ENTRY,
    CFGType.TRY_CATCH,
    CFGType.TRY_EXIT,

    # Break/continue/return: control flow is encoded in CFG edges
    CFGType.BREAK,
    CFGType.CONTINUE,
    CFGType.RETURN,
}


def _switch_match(switch_val: Any, case_val: Any) -> bool:
  """Return True when *switch_val* matches *case_val* using MATLAB semantics.

  * String / char-array equality is case-sensitive.
  * Cell case values ``{v1, v2, ...}`` match when any element matches.
  * Numeric scalars are compared element-wise.
  """
  # Cell case: {1, 2, 3} — match any element
  if isinstance(case_val, list):
    flat = [item for row in case_val for item in row]
    return any(_switch_match(switch_val, v) for v in flat)
  if isinstance(switch_val, str) and isinstance(case_val, str):
    return switch_val == case_val
  if isinstance(switch_val, torch.Tensor) and isinstance(case_val, torch.Tensor):
    try:
      return bool((switch_val == case_val).all())
    except (TypeError, RuntimeError):
      return False
  try:
    return switch_val == case_val
  except (TypeError, AttributeError):
    return False


class CodeControlExecutor(CodeExecutor):

  def __init__(self):
    super().__init__()
    self.for_loop = ContextManager(default_for)
    # Stack of evaluated switch-expression values for nested switch support
    self._switch_val_stack: List[Any] = []

  def eval(
    self, node: Expression | str,
    *args, **kwargs,
  ) -> Evaluated:
    if isinstance(node, str):
      if node == 'FOR_HAS_NEXT':
        return self.for_loop.current.has_next
      raise NotImplementedError(f'Unsupported string sentinel in eval: {node!r}')
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

    elif t == CFGType.SWITCH_ENTRY:
      stmt = cast(Switch_Statement, node.stmt_list)
      self._switch_val_stack.append(self.eval(stmt.n_expr))

    elif t in NO_OPR_TYPES:
      pass

    else:
      raise NotImplementedError(f'Unsupported CFG node type: {t}')

  def get_next_node(
      self,
      node_id: int,
      cfg: CFG,
  ) -> int:
    opts = cfg.next_node(node_id)
    node = cfg.node(node_id)

    # Switch: compare the stored switch value against each case expression
    if node.type == CFGType.SWITCH_ENTRY:
      switch_val = self._switch_val_stack[-1] if self._switch_val_stack else None
      otherwise_id = None
      for opt_id, cond in opts:
        if cond is None:
          if otherwise_id is None:
            otherwise_id = opt_id  # `otherwise` clause or no-match fallthrough
        else:
          case_val = self.eval(cond)
          if _switch_match(switch_val, case_val):
            return opt_id
      # No case matched — use `otherwise` (or no-match fallthrough) if available
      if otherwise_id is not None:
        return otherwise_id
      return STOP_ITR

    # Pop the switch value when leaving the switch block
    if node.type == CFGType.SWITCH_EXIT and self._switch_val_stack:
      self._switch_val_stack.pop()

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
      raise RuntimeError('CFG execution reached an unexpected dead end.')
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
