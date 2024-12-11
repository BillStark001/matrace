
import torch

from miss_hit_core.m_ast import *

from matrace.std.struct import create_struct

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
