from typing import List, Optional, cast

from miss_hit_core.m_ast import Script_File, Function_Definition, Function_File, Class_File


def get_function_by_name(
    ast: Function_File | Script_File | Class_File,
    name: Optional[str] = None,
):
  effective_name = name if name is not None else ast.name
  if effective_name.endswith('.m'):
    effective_name = effective_name[:-2]

  for f in cast(List[Function_Definition], ast.l_functions):
    f_name = f.n_sig.n_name.t_ident.value
    if f_name == effective_name:
      return f

  # When name was not specified and the AST carries no useful name (e.g. when
  # source is an in-memory code string), fall back to the first function.
  if name is None and ast.l_functions:
    return cast(List[Function_Definition], ast.l_functions)[0]

  return None
