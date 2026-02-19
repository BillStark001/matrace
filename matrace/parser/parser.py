from typing import Optional

from miss_hit_core.m_ast import Script_File, Function_Definition, Function_File, Class_File
from miss_hit_core.m_lexer import MATLAB_Lexer, MATLAB_Latest_Language
from miss_hit_core.config import Config
from miss_hit_core.errors import Message_Handler, Message
from miss_hit_core.m_parser import MATLAB_Parser


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
