from miss_hit_core.m_ast import *
from dataclasses import dataclass, field
from typing import List, Optional, Dict, cast, Any, Callable, Tuple, Union

from matrace.utils import ContextManager


class CFGType:
  
  SEQUENCE = 0
  
  GLOBAL_ENTRY = 1
  GLOBAL_EXIT = 2
  
  IF_ENTRY = 3
  IF_EXIT = 4
  IF_ACTION_ENTRY = 5
  
  SWITCH_ENTRY = 6
  SWITCH_EXIT = 7
  SWITCH_ACTION_ENTRY = 8
  
  FOR_ENTRY = 11
  FOR_EXIT = 12
  FOR_INIT = 13
  FOR_CONTINUE = 14
  
  WHILE_ENTRY = 15
  WHILE_EXIT = 16
  WHILE_CONTINUE = 17
  
  CONTINUE = 21
  BREAK = 22
  RETURN = 23
  
  SPMD_ENTRY = 28
  SPMD_EXIT = 29
  
  TRY_ENTRY = 41
  TRY_EXIT = 42
  TRY_CATCH = 43
  
  
@dataclass
class CFGNode:
  uid: int
  type: int = CFGType.SEQUENCE
  label: str = ''
  stmt_list: Optional[Sequence_Of_Statements] = None


@dataclass
class CFGEdge:
  from_node: int
  to_node: int
  label: str
  cond: Optional[Expression | str] = None
  precedence: Optional[int] = None

class CFGContext:
  
  def __init__(self):
    self.entry = ContextManager(0)
    self.exit = ContextManager(0)

@dataclass
class CFG:
  nodes: Dict[int, CFGNode] = field(default_factory=dict)
  edges: Dict[int, List[CFGEdge]] = field(default_factory=dict)
  current_id: int = 0
  
  entry_id: int = 0
  exit_id: int = 1
  
  ctx: CFGContext = field(default_factory=lambda: CFGContext())

  def add_node(
    self, 
    type: int,
    label: str = '', 
    stmt_list: Optional[Sequence_Of_Statements] = None
  ) -> int:
    node_id = self.current_id
    self.nodes[node_id] = CFGNode(node_id, type, label, stmt_list)
    self.current_id += 1
    return node_id

  def add_edge(
    self, 
    from_node: int, to_node: int, label: str, 
    cond: Optional[Expression] = None,
    precedence: int = 0,
  ):
    e = CFGEdge(from_node, to_node, label, cond, precedence)
    if from_node not in self.edges:
      self.edges[from_node] = []
    self.edges[from_node].append(e)
    self.edges[from_node].sort(key=lambda x: x.precedence)
    
  def node(self, id: int):
    return self.nodes[id]
  
  def next_node(self, id: int) -> List[Tuple[int, Union[Expression, None]]]:
    edges = self.edges[id]
    if len(edges) == 0:
      return [] if id == self.exit_id else [(self.exit_id, None)]
    return [(e.to_node, e.cond) for e in edges]


def generate_cfg(statements: Sequence_Of_Statements) -> CFG:
  cfg = CFG()
  ctx = CFGContext()
  cfg.ctx = ctx

  # Add entry and exit nodes
  entry_id = cfg.add_node(CFGType.GLOBAL_ENTRY, "Entry")
  exit_id = cfg.add_node(CFGType.GLOBAL_EXIT, "Exit")
  cfg.entry_id = entry_id
  cfg.exit_id = exit_id

  # Process statements
  with ctx.entry.provide(entry_id):
    with ctx.exit.provide(exit_id):
      last_id = process_statements(cfg, statements)

  # Connect last statement to exit node
  cfg.add_edge(last_id, exit_id, "End")

  return cfg

def is_sequential_statement(stmt):
  return isinstance(stmt, (
    Simple_Assignment_Statement, 
    Compound_Assignment_Statement, 
    Naked_Expression_Statement,
    # TODO should these be considered sequential?
    Global_Statement, 
    Persistent_Statement, 
    Import_Statement
  ))
  
def find_first_matching_index(
  lst: List[Any],
  condition: Callable[[Any], bool], 
  start = 0,
  fallback = -1
):
  return next((i for i in range(start, len(lst)) if condition(lst[i])), fallback)

def process_statements(
  cfg: CFG, 
  statements: Sequence_Of_Statements,
  start_id_override: Optional[int] = None,
) -> int:
  start_id = cfg.ctx.entry.current if start_id_override is None else start_id_override
  exit_id = cfg.ctx.exit.current
  current_id = start_id

  i = 0
  l = len(statements.l_statements)
  while i < l:
    stmt = statements.l_statements[i] # current statement
    prev_id = current_id
    
    # pack successive simple statements
    if is_sequential_statement(stmt):
      sequential_statement_end_index = find_first_matching_index(
        statements.l_statements,
        lambda x: not is_sequential_statement(x),
        i + 1,
        l
      )
      seq_stmts = statements.l_statements[i: sequential_statement_end_index]
      seq_obj = Sequence_Of_Statements(seq_stmts)
      
      current_id = cfg.add_node(
        CFGType.SEQUENCE,
        seq_obj.__class__.__name__, seq_obj
      )
      i = sequential_statement_end_index
      
    # simple statements with control flow
    elif isinstance(stmt, Simple_Statement):
      current_id = process_simple_control_statement(cfg, stmt, current_id)
      i += 1
    elif isinstance(stmt, Compound_Statement):
      current_id = process_compound_statement(cfg, stmt, current_id)
      i += 1
    
    cfg.add_edge(prev_id, current_id, 'Flow')  
    

  return current_id


def process_simple_control_statement(cfg: CFG, stmt: Simple_Statement, current_id: int) -> int:
  
  entry_id = cfg.ctx.entry.current
  exit_id = cfg.ctx.exit.current
  
  if isinstance(stmt, (Return_Statement, Break_Statement, Continue_Statement)):
    node_name = stmt.__class__.__name__[:-10]
    t = CFGType.RETURN # global exit id
    eid = cfg.exit_id
    if isinstance(stmt, Break_Statement):
      t = CFGType.BREAK
      eid = exit_id
    elif isinstance(stmt, Continue_Statement):
      t = CFGType.CONTINUE
      eid = entry_id
      
    node_id = cfg.add_node(t, node_name, stmt)
    cfg.add_edge(current_id, node_id, '->' + node_name)
    
    cfg.add_edge(node_id, eid, node_name)
    return node_id

  else:
    raise ValueError(f"Unknown simple control statement type: {type(stmt)}")


def process_compound_statement(cfg: CFG, stmt: Compound_Statement, current_id: int) -> int:
  if isinstance(stmt, For_Loop_Statement):
    return process_for_loop(cfg, stmt, current_id)
  elif isinstance(stmt, While_Statement):
    return process_while_loop(cfg, stmt, current_id)
  elif isinstance(stmt, If_Statement):
    return process_if_statement(cfg, stmt, current_id)
  elif isinstance(stmt, Switch_Statement):
    return process_switch_statement(cfg, stmt, current_id)
  elif isinstance(stmt, Try_Statement):
    return process_try_statement(cfg, stmt, current_id)
  elif isinstance(stmt, SPMD_Statement):
    return process_spmd_statement(cfg, stmt, current_id)
  else:
    raise ValueError(f"Unknown Compound_Statement type: {type(stmt)}")


def process_for_loop(cfg: CFG, stmt: For_Loop_Statement, current_id: int) -> int:
  loop_init = cfg.add_node(
    CFGType.FOR_INIT, 
    f"For Loop Init #{stmt.uid}", stmt
  )
  loop_cond = cfg.add_node(CFGType.FOR_ENTRY)
  loop_body_start = cfg.add_node(CFGType.FOR_CONTINUE)
  loop_exit = cfg.add_node(CFGType.FOR_EXIT, "For Loop Exit")
  
  cfg.add_edge(current_id, loop_init, "For Loop Init")
  cfg.add_edge(loop_init, loop_cond, "For Loop Condition")
  
  # this is not necessary, however by making this we made the flow clear
  cfg.add_edge(loop_cond, loop_body_start, 'For Body Start', 'FOR_HAS_NEXT', 0)
  cfg.add_edge(loop_cond, loop_exit, "Loop Complete", None, 1)

  # body of the for loop
  with cfg.ctx.entry.provide(loop_body_start): # for continue statements
    with cfg.ctx.exit.provide(loop_exit): # for break statements
      loop_body_end = process_statements(cfg, stmt.n_body)
  cfg.add_edge(loop_body_end, loop_cond, "Next Iteration")
  
  # Handle break statements
  # for node_id, node in cfg.nodes.items():
  #   if node.label == "Break" and node.stmt_list and node.stmt_list in stmt.n_body.l_statements:
  #     cfg.add_edge(node_id, loop_exit, "Break")

  return loop_exit


def process_while_loop(cfg: CFG, stmt: While_Statement, current_id: int) -> int:
  loop_start = cfg.add_node(CFGType.WHILE_ENTRY, f"While Loop #{stmt.uid}", stmt)
  loop_exit = cfg.add_node(CFGType.WHILE_EXIT, "While Loop Exit")
  loop_body_start = cfg.add_node(CFGType.WHILE_CONTINUE)
  
  cfg.add_edge(current_id, loop_start, "")

  with cfg.ctx.entry.provide(loop_body_start):
    with cfg.ctx.exit.provide(loop_exit):
      loop_body_end = process_statements(cfg, stmt.n_body)
  
  cfg.add_edge(loop_body_end, loop_start, 'Next Iteration')

  cfg.add_edge(loop_start, loop_body_start, "Condition True", stmt.n_guard, 0)
  cfg.add_edge(loop_start, loop_exit, "Condition False", None, 1)

  # Handle break statements
  # for node_id, node in cfg.nodes.items():
  #   if node.label == "Break" and node.stmt_list and node.stmt_list in stmt.n_body.l_statements:
  #     cfg.add_edge(node_id, loop_exit, "Break")

  return loop_exit


def process_if_statement(cfg: CFG, stmt: If_Statement, current_id: int) -> int:
  if_node = cfg.add_node(CFGType.IF_ENTRY, f"If #{stmt.uid}", stmt)
  # add an edge from the current one to `if` entry
  cfg.add_edge(current_id, if_node, "")

  end_if = cfg.add_node(CFGType.IF_EXIT, "End If")

  i_cur = 0
  with_else = False
  for i, action in enumerate(cast(List[Action], stmt.l_actions)):
    action_start = cfg.add_node(
      CFGType.IF_ACTION_ENTRY, 
      f"{action.kind()} Action #{i}", action
    )
    cfg.add_edge(
      if_node, action_start, action.kind(), 
      action.n_expr, i
    )
    i_cur = i
    if not with_else:
      with_else = action.n_expr is None
  if not with_else:
    cfg.add_edge(if_node, end_if, 'Default Else', None, i_cur + 1)

    action_end = process_statements(cfg, action.n_body, action_start)
    cfg.add_edge(action_end, end_if, "")

  return end_if

# TODO merge with if since almost identical
def process_switch_statement(cfg: CFG, stmt: Switch_Statement, current_id: int) -> int:
  switch_node = cfg.add_node(CFGType.SWITCH_ENTRY, f"Switch #{stmt.uid}", stmt)
  cfg.add_edge(current_id, switch_node, "")

  end_switch = cfg.add_node(CFGType.SWITCH_EXIT, "End Switch")

  for i, action in enumerate(cast(List[Action], stmt.l_actions)):
    action_start = cfg.add_node(CFGType.SWITCH_ACTION_ENTRY, f"{action.kind()} Action", action)
    cfg.add_edge(
      switch_node, action_start, action.kind(), 
      action.n_expr, i
    )

    action_end = process_statements(cfg, action.n_body, action_start)
    cfg.add_edge(action_end, end_switch, "")

  return end_switch


def process_try_statement(cfg: CFG, stmt: Try_Statement, current_id: int) -> int:
  try_node = cfg.add_node(CFGType.TRY_ENTRY, "Try", stmt)
  cfg.add_edge(current_id, try_node, "")

  try_body_end = process_statements(cfg, stmt.n_body, try_node)

  catch_node = cfg.add_node(CFGType.TRY_CATCH, "Catch", stmt)
  cfg.add_edge(try_node, catch_node, "Exception")

  catch_body_end = process_statements(cfg, stmt.n_handler, catch_node)

  end_try = cfg.add_node(CFGType.TRY_EXIT, "End Try")
  cfg.add_edge(try_body_end, end_try, "No Exception")
  cfg.add_edge(catch_body_end, end_try)

  return end_try


def process_spmd_statement(cfg: CFG, stmt: SPMD_Statement, current_id: int) -> int:
  spmd_node = cfg.add_node(CFGType.SPMD_ENTRY, "SPMD", stmt)
  cfg.add_edge(current_id, spmd_node)

  spmd_body_end = process_statements(cfg, stmt.n_body, spmd_node)

  end_spmd = cfg.add_node(CFGType.SPMD_EXIT, "End SPMD")
  cfg.add_edge(spmd_body_end, end_spmd)

  return end_spmd


