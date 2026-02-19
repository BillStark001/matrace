from typing import List, Optional, cast

from miss_hit_core.m_ast import Script_File, Function_Definition, Function_File, Class_File


def get_function_by_name(
    ast: Function_File | Script_File | Class_File,
    name: Optional[str] = None,
):
  name = name if name is not None else ast.name
  if name.endswith('.m'):
    name = name[:-2]

  for f in cast(List[Function_Definition], ast.l_functions):
    f_name = f.n_sig.n_name.t_ident.value
    if f_name == name:
      return f
  return None
