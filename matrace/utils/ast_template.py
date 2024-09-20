from typing import List, Dict, Tuple, Optional, Callable, TypeAlias

import ast
import copy

from matrace.utils import gen_uuid_b64


Replacer: TypeAlias = Optional[str | ast.AST | Callable[[ast.AST], ast.AST]]

class VariableVisitor(ast.NodeVisitor):

  def __init__(self):
    self.var_dict: Dict[str, List[ast.Name]] = {}

  def visit_Name(self, node: ast.Name):
    name = node.id
    if not name in self.var_dict:
      self.var_dict[name] = []
    self.var_dict[name].append(node)
    
    
class VariableReplacer(ast.NodeTransformer):
  
  def __init__(self, **replacers: Replacer):
    self.replacers = replacers
    self.none_replacers: List[str] = []
    for src, dst in self.replacers.items():
      if dst is None:
        self.none_replacers.append(src)
    
  def refresh(self):
    for src in self.none_replacers:
      self.replacers[src] = 'var_' + gen_uuid_b64()
    
  def visit_Name(self, node: ast.Name):
    name = node.id
    if not name in self.replacers:
      return self.generic_visit(node)
    
    repl = self.replacers[name]
    if isinstance(repl, str):
      node.id = repl
      return self.generic_visit(node)
    elif isinstance(repl, ast.AST):
      return repl
    elif callable(repl):
      return repl(node)
    
    return self.generic_visit(node)


def create_var_dict(node: ast.AST):
  v = VariableVisitor()
  v.visit(node)
  return v.var_dict

class CodeTemplate:

  def __init__(
      self,
      template: str | Callable,
      mode: str = 'eval',
      **default_replace: Replacer
  ):
    self.tree: ast.Module = ast.parse(template, mode=mode)
    self.var_dict = create_var_dict(self.tree)
    self.default_replace = default_replace
    
  def fill_default_replacers(self, replace_args: Dict[str, Replacer]):

    for src, dst in self.default_replace.items():
      if not src in replace_args:
        replace_args[src] = dst
        
    return replace_args
  
  def compile_non_ast_replacers(self, replace_args: Dict[str, Replacer]):

    for src, dst in replace_args.items():
      if not isinstance(dst, ast.AST) and not isinstance(dst, str):
        replace_args[src] = ast.Constant(dst)
        
    return replace_args
        
  def gen_hash_for_replacers(self, replace_args: Dict[str, Replacer]):
    
    for src, dst in replace_args.items():
      if dst is None:
        replace_args[src] = 'var_' + gen_uuid_b64()
        
    return replace_args
    
  def create(self, **replace_args: Replacer):
    
    self.fill_default_replacers(replace_args)
    self.compile_non_ast_replacers(replace_args)
    
    replacer = VariableReplacer(**replace_args)
    replacer.refresh()
    
    tree_copy = copy.deepcopy(self.tree)
    replacer.visit(tree_copy)
    return tree_copy

  def create_naive(self, **replace_args: Replacer):
    
    self.fill_default_replacers(replace_args)
    self.gen_hash_for_replacers(replace_args)

    # check optional arguments
    for src, dst in self.default_replace.items():
      if not src in replace_args:
        replace_args[src] = dst
    for src, dst in replace_args.items():
      if dst is None:
        replace_args[src] = 'var_' + gen_uuid_b64()

    # replace in-place

    replaced: List[Tuple[ast.Name, str]] = []

    for src, dst in replace_args.items():
      if not src in self.var_dict:
        continue
      for node in self.var_dict[src]:
        if isinstance(dst, str):
          node.id = dst
          replaced.append((node, src))

    # copy tree
    tree_copy = copy.deepcopy(self.tree)

    for node, src in replaced:
      node.id = src

    return tree_copy
