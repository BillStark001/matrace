from typing import cast, Optional, List

from miss_hit_core.m_ast import *
from miss_hit_core.m_lexer import MATLAB_Lexer, MATLAB_Latest_Language
from miss_hit_core.config import Config
from miss_hit_core.errors import Message_Handler, Message
from miss_hit_core.m_parser import MATLAB_Parser


class ModifiedMessageHandler(Message_Handler):
  def __init__(self, config):
    super().__init__(config)

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