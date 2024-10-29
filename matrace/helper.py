from typing import cast, Optional, List, overload, Tuple, Callable, Literal

import json

from miss_hit_core.m_ast import Script_File, Function_Definition, Function_File, Class_File
from miss_hit_core.m_lexer import MATLAB_Lexer, MATLAB_Latest_Language
from miss_hit_core.config import Config
from miss_hit_core.errors import Message_Handler, Message
from miss_hit_core.m_parser import MATLAB_Parser

from matrace.exec_cfg import exec_func


class ModifiedMessageHandler(Message_Handler):

  def register_message(self, msg):
    assert isinstance(msg, Message)
    self.process_message(msg)
    if msg.fatal:
      raise Exception(msg.location, msg.message)


def parse_matlab_code(content: str, path: Optional[str] = None):

  mh = ModifiedMessageHandler('debug')

  lexer = MATLAB_Lexer(
      MATLAB_Latest_Language(),
      mh,
      content,
      path,
      None
  )

  cfg = Config()
  cfg.style_rules = {}

  parser = MATLAB_Parser(
      mh,
      lexer,
      cfg,
  )

  cu = parser.parse_file()
  return cu


def get_function_by_name(ast: Function_File | Script_File | Class_File, name: Optional[str] = None):
  name = name if name is not None else ast.name
  if name.endswith('.m'):
    name = name[:-2]
    
  for f in cast(List[Function_Definition], ast.l_functions):
    f_name = f.n_sig.n_name.t_ident.value
    if f_name == name:
      return f
  return None


def _get_func(cu: Function_File | Script_File | Class_File, fname: str | None, scope=dict):
  func_ast = get_function_by_name(cu, name=fname)
  fname_pretty = json.dumps(
          fname) if fname is not None else '<default>'
  assert func_ast is not None, \
      f'Function not found: {fname_pretty}'

  def wrapped_func(*args):
    # pylint: disable=W0104, W0640
    f'''Imported MATLAB function: {fname_pretty}'''
    # pylint: disable=W0640
    return exec_func(func_ast, args, scope)
  
  return func_ast, wrapped_func

@overload
def import_matlab_func(
    path_or_code: str,
    scope: dict | None = None,
    is_code=False,
    return_ast: Literal[False] = False,
    function_name: str | None = None,
) -> Callable:
  pass


@overload
def import_matlab_func(
    path_or_code: str,
    scope: dict | None = None,
    is_code=False,
    return_ast: Literal[False] = False,
    function_name: List[str | None] = None,
) -> List[Callable]:
  pass


@overload
def import_matlab_func(
    path_or_code: str,
    scope: dict | None = None,
    is_code=False,
    return_ast: Literal[True] = True,
    function_name: str | None = None,
) -> Tuple[Function_Definition, Callable]:
  pass


@overload
def import_matlab_func(
    path_or_code: str,
    scope: dict | None = None,
    is_code=False,
    return_ast: Literal[True] = True,
    function_name: List[str | None] = None,
) -> List[Tuple[Function_Definition, Callable]]:
  pass


def import_matlab_func(
    path_or_code: str,
    scope: dict | None = None,
    function_name: str | List[str | None] | None = None,
    is_code=False,
    return_ast=False,
):

  content = path_or_code
  if not is_code:
    with open(path_or_code, "r", encoding="utf-8") as f:
      content = f.read()

  cu = parse_matlab_code(content, path_or_code if not is_code else '')

  is_mono = False
  if not isinstance(function_name, list):
    is_mono = True
    function_name = [function_name]

  ret = []
  for fname in function_name:

    func_ast, wrapped_func = _get_func(cu, fname, scope=scope if scope is not None else {})

    ret.append((func_ast, wrapped_func) if return_ast else wrapped_func)

  if is_mono:
    return ret[0]
  return ret
