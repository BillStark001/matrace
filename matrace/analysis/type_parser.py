"""JSDoc-style MATLAB type-annotation parser (Phase 2.2).

Grammar
-------
::

    type_expr := "any"
               | "scalar" dtype
               | "vector" ("<" dim ">")? dtype
               | "matrix" ("<" dim "," dim ">")? dtype
               | "cell" ("<" type_expr ">")?
               | "struct" "<" "{" field_list "}" ">"
               | <name>  # extensible via TYPE_REGISTRY

    field_list := name ":" type_expr ("," name ":" type_expr)*
    dtype      := "float" | "int" | "logical"
    dim        := <integer> | "any"

Public API
----------
* :func:`parse_type_str` – parse a type-expression string into a
  :class:`~matrace.types.base.MatraceType`.
* :func:`extract_func_annotations` – extract ``@param`` / ``@returns``
  annotations from the comments that precede a MATLAB function definition.
* :class:`FuncAnnotation` – dataclass holding the result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matrace.types.base import AnyType, MatraceType
from matrace.types.cell import CellType
from matrace.types.dtypes import DTYPES
from matrace.types.function import FunctionType
from matrace.types.matrix import MatrixType, VectorType
from matrace.types.registry import TYPE_REGISTRY
from matrace.types.scalar import ScalarType
from matrace.types.struct import StructType

if TYPE_CHECKING:
    from miss_hit_core.m_ast import Function_Definition

# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

_TK_WORD   = "WORD"    # identifier / keyword
_TK_INT    = "INT"     # integer literal
_TK_LT     = "LT"     # <
_TK_GT     = "GT"     # >
_TK_COMMA  = "COMMA"  # ,
_TK_LBRACE = "LBRACE" # {
_TK_RBRACE = "RBRACE" # }
_TK_COLON  = "COLON"  # :
_TK_END    = "END"    # sentinel

_TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(\d+)"             # group 1 – integer
    r"|([A-Za-z_]\w*)"  # group 2 – word
    r"|(<)"             # group 3
    r"|(>)"             # group 4
    r"|(,)"             # group 5
    r"|(\{)"            # group 6
    r"|(\})"            # group 7
    r"|(:)"             # group 8
    r")"
)

_Token = tuple[str, object]


def _tokenize(s: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if m is None or m.start() == m.end():
            raise ValueError(
                f"Unexpected character at position {pos} in type string: {s[pos:]!r}"
            )
        if m.group(1):
            tokens.append((_TK_INT, int(m.group(1))))
        elif m.group(2):
            tokens.append((_TK_WORD, m.group(2)))
        elif m.group(3):
            tokens.append((_TK_LT, "<"))
        elif m.group(4):
            tokens.append((_TK_GT, ">"))
        elif m.group(5):
            tokens.append((_TK_COMMA, ","))
        elif m.group(6):
            tokens.append((_TK_LBRACE, "{"))
        elif m.group(7):
            tokens.append((_TK_RBRACE, "}"))
        elif m.group(8):
            tokens.append((_TK_COLON, ":"))
        pos = m.end()
    tokens.append((_TK_END, None))
    return tokens


# ---------------------------------------------------------------------------
# Recursive-descent parser
# ---------------------------------------------------------------------------

class _TypeParser:
    """Internal recursive-descent parser for type-expression strings.

    This class is also the argument type received by custom parser functions
    registered in :data:`~matrace.types.registry.TYPE_REGISTRY`.  Your
    function may call any of the public helpers below.
    """

    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # -- low-level helpers --------------------------------------------------

    def peek(self) -> _Token:
        """Return the current token without consuming it."""
        return self._tokens[self._pos]

    def consume(
        self,
        kind: str | None = None,
        value: object = None,
    ) -> _Token:
        """Consume and return the current token.

        Args:
            kind:  If given, asserts that the current token has this kind.
            value: If given, asserts that the current token has this value.

        Raises:
            ValueError: On a mismatch.
        """
        tok = self._tokens[self._pos]
        if kind is not None and tok[0] != kind:
            raise ValueError(
                f"Expected token kind {kind!r} but got {tok[0]!r} ({tok[1]!r})"
            )
        if value is not None and tok[1] != value:
            raise ValueError(
                f"Expected token value {value!r} but got {tok[1]!r}"
            )
        self._pos += 1
        return tok

    # -- grammar helpers ----------------------------------------------------

    def parse_dim(self) -> int | None:
        """Parse a dimension argument: integer or ``"any"`` → ``int | None``."""
        tok = self.peek()
        if tok[0] == _TK_INT:
            self.consume()
            return int(tok[1])
        if tok[0] == _TK_WORD and tok[1] == "any":
            self.consume()
            return None
        raise ValueError(
            f"Expected dimension (integer or 'any') but got {tok[0]!r} ({tok[1]!r})"
        )

    def parse_dtype(self) -> str:
        """Parse a dtype keyword: ``float | int | logical``."""
        tok = self.consume(_TK_WORD)
        if tok[1] not in DTYPES:
            raise ValueError(
                f"Expected dtype (float / int / logical) but got {tok[1]!r}"
            )
        return str(tok[1])

    def parse_type(self) -> MatraceType:
        """Parse a full type expression and return a :class:`MatraceType`."""
        tok = self.peek()
        if tok[0] != _TK_WORD:
            raise ValueError(
                f"Expected a type keyword but got {tok[0]!r} ({tok[1]!r})"
            )
        name = str(tok[1])
        self.consume()

        # -- built-in types -------------------------------------------------

        if name == "any":
            return AnyType()

        if name == "scalar":
            dtype = self.parse_dtype()
            return ScalarType(dtype=dtype)  # type: ignore[arg-type]

        if name == "vector":
            length: int | None = None
            if self.peek()[0] == _TK_LT:
                self.consume(_TK_LT)
                length = self.parse_dim()
                self.consume(_TK_GT)
            dtype = self.parse_dtype()
            return VectorType(dtype=dtype, length=length)  # type: ignore[arg-type]

        if name == "matrix":
            rows: int | None = None
            cols: int | None = None
            if self.peek()[0] == _TK_LT:
                self.consume(_TK_LT)
                rows = self.parse_dim()
                self.consume(_TK_COMMA)
                cols = self.parse_dim()
                self.consume(_TK_GT)
            dtype = self.parse_dtype()
            return MatrixType(dtype=dtype, rows=rows, cols=cols)  # type: ignore[arg-type]

        if name == "cell":
            element_type: MatraceType = AnyType()
            if self.peek()[0] == _TK_LT:
                self.consume(_TK_LT)
                element_type = self.parse_type()
                self.consume(_TK_GT)
            return CellType(element_type=element_type)

        if name == "struct":
            fields: dict[str, MatraceType] = {}
            self.consume(_TK_LT)
            self.consume(_TK_LBRACE)
            while self.peek()[0] != _TK_RBRACE:
                f_name = str(self.consume(_TK_WORD)[1])
                self.consume(_TK_COLON)
                f_type = self.parse_type()
                fields[f_name] = f_type
                if self.peek()[0] == _TK_COMMA:
                    self.consume()
            self.consume(_TK_RBRACE)
            self.consume(_TK_GT)
            return StructType(fields=fields)

        # -- extensible registry --------------------------------------------

        if name in TYPE_REGISTRY:
            return TYPE_REGISTRY[name](self)

        raise ValueError(
            f"Unknown type keyword {name!r}. "
            "Register a custom parser via matrace.types.register_type_parser()."
        )


# ---------------------------------------------------------------------------
# Public: parse a type string
# ---------------------------------------------------------------------------

def parse_type_str(s: str) -> MatraceType:
    """Parse a type-expression string and return the corresponding type object.

    Args:
        s: A type-expression string, e.g. ``"scalar float"``,
           ``"matrix<3,3> float"``, ``"cell<scalar int>"``.

    Returns:
        A :class:`~matrace.types.base.MatraceType` instance.

    Raises:
        ValueError: If the string cannot be parsed.

    Examples::

        >>> parse_type_str("scalar float")
        ScalarType(dtype='float')
        >>> parse_type_str("matrix<any,any> float")
        MatrixType<any,any>(dtype='float')
        >>> parse_type_str("cell<scalar int>")
        CellType<any,any>(element=ScalarType(dtype='int'))
    """
    tokens = _tokenize(s.strip())
    parser = _TypeParser(tokens)
    result = parser.parse_type()
    # Ensure we consumed the whole input (trailing _TK_END is fine)
    if parser.peek()[0] != _TK_END:
        remaining = s[sum(len(str(t[1])) for t in tokens[:parser._pos]):]
        raise ValueError(
            f"Unexpected trailing tokens after type expression: {remaining!r}"
        )
    return result


# ---------------------------------------------------------------------------
# Annotation comment extraction
# ---------------------------------------------------------------------------

def _find_matching_brace(s: str, start: int) -> int:
    """Return the index of the ``}`` that closes the ``{`` at *start*.

    Raises:
        ValueError: If the braces are not balanced.
    """
    assert s[start] == "{"
    depth = 1
    i = start + 1
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"Unmatched '{{' in annotation string: {s[start:]!r}")


def _parse_param_line(line: str) -> tuple[str, str] | None:
    """Parse a ``@param`` annotation line.

    Returns ``(type_str, param_name)`` or ``None`` if the line does not match.
    Handles nested braces (e.g. struct field lists) correctly.
    """
    m = re.match(r"^\s*%\s*@param\s+", line, re.IGNORECASE)
    if not m:
        return None
    rest = line[m.end():]
    if not rest.startswith("{"):
        return None
    try:
        close = _find_matching_brace(rest, 0)
    except ValueError:
        return None
    type_str = rest[1:close].strip()
    after = rest[close + 1:]
    m2 = re.match(r"\s+(\w+)", after)
    if not m2:
        return None
    return type_str, m2.group(1)


def _parse_returns_line(line: str) -> str | None:
    """Parse a ``@returns`` / ``@return`` annotation line.

    Returns the type-string or ``None`` if the line does not match.
    Handles nested braces correctly.
    """
    m = re.match(r"^\s*%\s*@returns?\s+", line, re.IGNORECASE)
    if not m:
        return None
    rest = line[m.end():]
    if not rest.startswith("{"):
        return None
    try:
        close = _find_matching_brace(rest, 0)
    except ValueError:
        return None
    return rest[1:close].strip()


@dataclass
class FuncAnnotation:
    """Type annotations extracted from JSDoc-style MATLAB comments.

    Attributes:
        params: Mapping of parameter name → annotated :class:`MatraceType`.
        returns: Ordered list of return-value :class:`MatraceType` objects.
    """

    params: dict[str, MatraceType] = field(default_factory=dict)
    returns: list[MatraceType] = field(default_factory=list)

    def __repr__(self) -> str:
        p = {k: repr(v) for k, v in self.params.items()}
        r = [repr(t) for t in self.returns]
        return f"FuncAnnotation(params={p}, returns={r})"


def extract_func_annotations(
    func_ast: "Function_Definition",
    source: str,
) -> FuncAnnotation:
    """Extract JSDoc-style type annotations for a MATLAB function.

    The function scans the comment lines that immediately precede the
    ``function`` keyword in *source* and parses any ``@param`` /
    ``@returns`` tags it finds.

    Args:
        func_ast: The parsed :class:`~miss_hit_core.m_ast.Function_Definition`
            node (used to determine the line number of the ``function``
            keyword).
        source: The full source text of the MATLAB file.

    Returns:
        A :class:`FuncAnnotation` with the extracted type information.
        Annotations that cannot be parsed are silently skipped.

    Example (in MATLAB source)::

        % @param {scalar float} x - Input value
        % @param {matrix<3,3> float} A - 3×3 matrix
        % @returns {scalar float} - Result
        function y = my_func(x, A)
            y = x * sum(A(:));
        end
    """
    annotation = FuncAnnotation()

    # Locate the 'function' keyword line (1-based).
    func_line = func_ast.t_fun.location.line  # 1-based

    lines = source.splitlines()
    # Collect consecutive comment lines immediately before the function.
    comment_lines: list[str] = []
    for i in range(func_line - 2, -1, -1):  # walk upwards from line before
        stripped = lines[i].strip()
        if stripped.startswith("%") or stripped == "":
            comment_lines.insert(0, lines[i])
        else:
            break

    for line in comment_lines:
        # Try @param
        result = _parse_param_line(line)
        if result is not None:
            type_str, param_name = result
            try:
                annotation.params[param_name] = parse_type_str(type_str)
            except ValueError:
                pass  # skip malformed annotation
            continue

        # Try @returns / @return
        type_str = _parse_returns_line(line)
        if type_str is not None:
            try:
                annotation.returns.append(parse_type_str(type_str))
            except ValueError:
                pass  # skip malformed annotation

    return annotation
