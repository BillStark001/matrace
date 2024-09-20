
import torch

from miss_hit_core.m_ast import *

from matrace.miss_hit_helper import get_function_by_name, parse_matlab_code
from matrace.src_exec_cfg import exec_func
from matrace.utils import DictWrapper

def create_struct(*args):
  d = {}
  for i in range(0, len(args), 2):
    d[args[i]] = args[i + 1]
  return DictWrapper(d)

global_funcs = {
  'size': lambda a: tuple(a.size()),
  'error': print,
  'eig': lambda a: torch.linalg.eig(a).eigenvalues,
  'sum': lambda a: torch.sum(a).reshape((1, 1)),
  # TODO
  'struct': create_struct,
  'isequal': lambda a, b: torch.all(a == b),
  'det': torch.det,
  'disp': print,
  'NaN': torch.nan,
  'numel': torch.numel,
}

def import_matlab_func(path: str):

  with open(path, "r", encoding="utf-8") as f:
    content = f.read()
  
  cu = parse_matlab_code(content, path)
  
  assert isinstance(cu, Function_File)

  func_main = get_function_by_name(cu)

  def wrapped_func(*args):
    return exec_func(func_main, args, global_funcs)
  
  return func_main, wrapped_func

