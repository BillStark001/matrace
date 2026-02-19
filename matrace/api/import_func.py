from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Tuple, overload

from miss_hit_core.m_ast import Function_Definition

from matrace.analysis.type_parser import FuncAnnotation, extract_func_annotations
from matrace.parser.parser import parse_matlab_code
from matrace.parser.ast_utils import get_function_by_name
from matrace.interpreter.cfg_executor import exec_func

import json


def _get_func(cu, fname: str | None, scope: dict, content: str):
  func_ast = get_function_by_name(cu, name=fname)
  fname_pretty = json.dumps(fname) if fname is not None else '<default>'
  assert func_ast is not None, f'Function not found: {fname_pretty}'

  annotation = extract_func_annotations(func_ast, content)

  def wrapped_func(*args):
    # pylint: disable=W0104, W0640
    f'''Imported MATLAB function: {fname_pretty}'''
    # pylint: disable=W0640
    return exec_func(func_ast, args, scope)

  return func_ast, annotation, wrapped_func


@overload
def import_matlab_func(
    source: str | Path,
    *,
    function_name: str | None = None,
    scope: Dict[str, Any] | None = None,
    is_code: bool = False,
    return_ast: Literal[False] = False,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: Dict[str, Any] | None = None,
) -> Callable:
  pass


@overload
def import_matlab_func(
    source: str | Path,
    *,
    function_name: List[str | None],
    scope: Dict[str, Any] | None = None,
    is_code: bool = False,
    return_ast: Literal[False] = False,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: Dict[str, Any] | None = None,
) -> List[Callable]:
  pass


@overload
def import_matlab_func(
    source: str | Path,
    *,
    function_name: str | None = None,
    scope: Dict[str, Any] | None = None,
    is_code: bool = False,
    return_ast: Literal[True] = True,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: Dict[str, Any] | None = None,
) -> Tuple[Function_Definition, FuncAnnotation, Callable]:
  pass


@overload
def import_matlab_func(
    source: str | Path,
    *,
    function_name: List[str | None],
    scope: Dict[str, Any] | None = None,
    is_code: bool = False,
    return_ast: Literal[True] = True,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: Dict[str, Any] | None = None,
) -> List[Tuple[Function_Definition, FuncAnnotation, Callable]]:
  pass


def import_matlab_func(
    source: str | Path,
    *,
    function_name: str | List[str | None] | None = None,
    scope: Dict[str, Any] | None = None,
    is_code: bool = False,
    return_ast: bool = False,
    compile_mode: Literal["auto", "static", "dynamic"] = "auto",
    type_hints: Dict[str, Any] | None = None,
):
  """
  Import MATLAB function(s) as Python callables.

  Args:
      source: File path or code string
      function_name: Name(s) of function(s) to import
      scope: External functions to inject
      is_code: True if source is code string, False if file path
      return_ast: When ``True``, return ``(ast, annotation, callable)`` tuples
          instead of bare callables.  *annotation* is a
          :class:`~matrace.analysis.type_parser.FuncAnnotation` built from
          the JSDoc-style comments that precede the function.
      compile_mode:
          - "auto": Use static if types available, else dynamic (currently same as dynamic)
          - "static": Force static compilation (error if types missing; not yet implemented)
          - "dynamic": Force dynamic interpretation
      type_hints: Optional type hints for parameters (reserved for future use)

  Returns:
      Callable or list of callables.  When *return_ast* is ``True``, each
      element becomes a ``(Function_Definition, FuncAnnotation, callable)``
      tuple.
  """
  if compile_mode == "static":
    raise NotImplementedError(
        "Static compilation is not yet implemented. Use compile_mode='dynamic' or 'auto'."
    )

  content = str(source)
  if not is_code:
    with open(source, "r", encoding="utf-8") as f:
      content = f.read()

  cu = parse_matlab_code(content, str(source) if not is_code else '')

  is_mono = False
  if not isinstance(function_name, list):
    is_mono = True
    function_name = [function_name]

  ret = []
  for fname in function_name:
    func_ast, annotation, wrapped_func = _get_func(
        cu, fname,
        scope=scope if scope is not None else {},
        content=content,
    )
    ret.append((func_ast, annotation, wrapped_func) if return_ast else wrapped_func)

  if is_mono:
    return ret[0]
  return ret
