from typing import cast, Dict, Any, Tuple, Callable, TypeVar, ParamSpec, Generic

import ast
import inspect
import copy

from matrace.utils.ast_template import CodeTemplate
from matrace.utils.context import ContextManager
from matrace.utils.gen_uuid import gen_uuid_b64


class BranchEvent:
  IF = 0
  ELIF = 1
  ELSE = 2

  MATCH_CASE = 10
  MATCH_DEFAULT = 11

  FOR = 20

  WHILE = 30


tpl_create_tracer = CodeTemplate('''
tracer = {}
for_record = None
tracer_stack = [tracer]
for_stack = []
''', mode='exec')
tpl_add_tracer = CodeTemplate('tracer_stack[-1][lineno] = (event, data)', mode='exec')
tpl_ret_assign = CodeTemplate('return (return_body), tracer', mode='exec')

# TODO
tpl_init_for = CodeTemplate('''
for_record = []
tracer_stack[-1][lineno] = (event, for_record)
for_stack.append(for_record)
''', mode='exec')

tpl_before_for = CodeTemplate('''
cur_tracer = {}
for_stack[-1].append((for_body, cur_tracer))
tracer_stack.append(cur_tracer)
''', mode='exec')

tpl_after_for = CodeTemplate('tracer_stack.pop()', mode='exec')

tpl_end_for = CodeTemplate('for_stack.pop()', mode='exec')

tpl_eq = CodeTemplate('a = b', mode='exec')


none_node = ast.parse('None').body[0].value


def strip_leading_spaces(source: str):
  space_count = len(source) - len(source.lstrip(' \t'))
  if space_count > 0:
    source_splitted = [(
        x[space_count:] if len(x) > space_count else ''
    ) for x in source.split('\n')]
    source = '\n'.join(source_splitted)
  return source


class BranchTracedCompiler(ast.NodeTransformer):
  def __init__(self, expand_for=True):
    self.uuid = gen_uuid_b64()[:16:2] \
      .replace('-', '_').replace('+', '_').replace(':', '_').replace('=', '_')
    self.def_dict = {
      key: f'_{key}_{self.uuid}'
      for key in [
        'tracer', 'for_record', 
        'tracer_stack', 'for_stack', 
        'cur_tracer']
    }
    self.expand_for=expand_for

  def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
    new_node: ast.FunctionDef = self.generic_visit(copy.deepcopy(node))
    new_node.body = [
        *tpl_create_tracer.create(**self.def_dict).body,
        *new_node.body,
    ]
    return new_node
  
  def visit_For(self, node: ast.For) -> Any:
    if not self.expand_for:
      return self.generic_visit(node)
    lineno = node.lineno
    line_dict = dict(lineno=lineno, data=node.iter)
    new_node: ast.For = self.generic_visit(copy.copy(node))
    new_node.body = [
        *tpl_before_for.create(**self.def_dict, for_body=node.target).body,
        *new_node.body,
        *tpl_after_for.create(**self.def_dict).body,
    ]
    new_node_outer = [
      *tpl_init_for.create(
        **self.def_dict, **line_dict, event=BranchEvent.FOR
      ).body,
      new_node,
      *tpl_end_for.create(**self.def_dict).body,
    ]
    return new_node_outer

  def visit_If(self, node):
    lineno = node.lineno
    line_dict = dict(lineno=lineno, data=none_node)
    new_node: ast.If = self.generic_visit(copy.copy(node))
    new_node.body = [
        *tpl_add_tracer.create(**self.def_dict, **line_dict,
                               event=BranchEvent.IF).body,
        *new_node.body,
    ]
    if hasattr(new_node, 'orelse') and not isinstance(new_node.orelse[0], ast.If):
      # this means it is an `else:` branch
      new_node.orelse = [
          *tpl_add_tracer.create(**self.def_dict, **line_dict,
                                 event=BranchEvent.ELSE).body,
          *new_node.orelse,
      ]

    return new_node

  def visit_Return(self, node: ast.Return) -> ast.Return:
    ret_assign = tpl_ret_assign.create(
        **self.def_dict, return_body=copy.copy(node.value)).body
    return ret_assign


class BranchRemover(ast.NodeTransformer):
  def __init__(
    self, 
    executed_lines: Dict[int, Tuple[int, Any]],
    expand_for=True,
  ):
    self.uuid = gen_uuid_b64()
    self.exec = ContextManager(executed_lines)
    self.expand_for = expand_for
    
  def _gv(self, v): return [self.generic_visit(x) for x in v]
  def _v(self, v): return [self.visit(x) for x in v]

  def visit_If(self, node):
    if node.lineno in self.exec.current:
      (event, _) = self.exec.current[node.lineno]
      if event == BranchEvent.ELSE:
        return self._gv(node.orelse)
      else:
        return self._gv(node.body)
    elif hasattr(node, 'orelse') and node.orelse:
      return self._gv(node.orelse)
    return None
  
  def visit_For(self, node):
    if not self.expand_for:
      return self.generic_visit(node)
    if not node.lineno in self.exec.current:
      return None
    _, for_record = self.exec.current[node.lineno]
    acc_stack = []
    for (for_elem, trace) in for_record:
      with self.exec.provide(trace):
        # inject names to replace
        acc_stack += tpl_eq.create(a=node.target, b=for_elem).body
        acc_stack += self._v(node.body)
    return acc_stack

P = ParamSpec('P')
R = TypeVar('R')


class FunctionTracer(Generic[P, R]):

  def __init__(self, func: Callable[P, R], expand_for=True) -> None:
    self.func = func
    self.source = strip_leading_spaces(inspect.getsource(func))
    self.expand_for=expand_for

    # get the function ast
    tree = ast.parse(self.source)
    self.func_def: ast.FunctionDef = tree.body[0]

    # traced function
    cmp = BranchTracedCompiler(expand_for=self.expand_for)
    traced_func = cmp.visit(self.func_def)
    self.traced_func_str = ast.unparse(traced_func)

    local_ns = {}
    exec(self.traced_func_str, globals(), local_ns)
    self.traced_func = local_ns[self.func_def.name]

  def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
    return self.func(*args, **kwargs)

  def prune(self, *args: P.args, **kwargs: P.kwargs) -> Tuple[R, str]:
    ret, trace = self.traced_func(*args, **kwargs)
    repl = BranchRemover(trace, expand_for=self.expand_for)
    new_tree = repl.visit(self.func_def)
    new_source = ast.unparse(new_tree)

    return ret, new_source

  def prune_f(self, *args: P.args, **kwargs: P.kwargs) -> Tuple[R, Callable[P, R]]:
    ret, src = self.prune(*args, **kwargs)

    local_ns = {}
    exec(src, globals(), local_ns)
    f = local_ns[self.func_def.name]

    return ret, f


if __name__ == "__main__":

  def example_function(x: int):
    j = []
    for i in range(-x, 10 + x):
      if i > 5:
        j.append(i - 5)
      else:
        j.append(5 - i)
    if x > 0:
      return "Positive", j
    elif x < 0:
      return "Negative", j
    else:
      return "Zero", j

  t = FunctionTracer(example_function)

  _, optimized_source = t.prune(3)
  _, f = t.prune_f(3)

  print(optimized_source)
  print(f(-3))
