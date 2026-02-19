"""Extensible registry that maps type-keyword strings to parser callables.

How to add a new type
---------------------
1. Subclass :class:`~matrace.types.base.MatraceType`.
2. Write a *parser function* with the signature::

       def my_type_parser(parser: "_TypeParser") -> MatraceType: ...

   ``_TypeParser`` is the recursive-descent parser instance defined in
   :mod:`matrace.analysis.type_parser`.  You can call any of its public
   helpers (``consume``, ``peek``, ``parse_dim``, ``parse_type``, …) to
   consume tokens from the type-string stream.

3. Register it::

       from matrace.types.registry import register_type_parser
       register_type_parser("mytype", my_type_parser)

   After registration, ``parse_type_str("mytype …")`` will invoke your
   function automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from matrace.analysis.type_parser import _TypeParser
    from matrace.types.base import MatraceType

#: Maps a type-keyword (e.g. ``"scalar"``) to a callable that receives the
#: :class:`~matrace.analysis.type_parser._TypeParser` instance and returns a
#: constructed :class:`~matrace.types.base.MatraceType`.
TYPE_REGISTRY: dict[str, Callable["_TypeParser", "MatraceType"]] = {}


def register_type_parser(
    name: str,
    parser_fn: Callable["_TypeParser", "MatraceType"],
) -> None:
    """Register *parser_fn* as the constructor for type-keyword *name*.

    Args:
        name: The keyword that appears in type annotation strings (e.g.
            ``"scalar"``, ``"mytype"``).
        parser_fn: A callable ``(parser: _TypeParser) -> MatraceType`` that
            consumes tokens from the stream and returns a constructed type.

    Raises:
        ValueError: If *name* is already registered and the existing entry is
            different from *parser_fn*.
    """
    existing = TYPE_REGISTRY.get(name)
    if existing is not None and existing is not parser_fn:
        raise ValueError(
            f"Type keyword {name!r} is already registered by {existing!r}. "
            "Use a different keyword or explicitly overwrite via "
            "TYPE_REGISTRY[name] = parser_fn."
        )
    TYPE_REGISTRY[name] = parser_fn
