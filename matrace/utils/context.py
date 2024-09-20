from typing import TypeVar, Generic, List


T = TypeVar("T")


class ContextManager(Generic[T]):
  def __init__(self, default: T = None):
    self._default = default
    self._context_stack: List[T] = []

  def push(self, context: T):
    self._context_stack.append(context)

  def pop(self):
    if self._context_stack:
      return self._context_stack.pop()
    raise IndexError("pop from empty context stack")

  @property
  def current(self) -> T:
    if self._context_stack:
      return self._context_stack[-1]
    return self._default

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.pop()

  def provide(self, context: T):
    """Context manager method to use a context."""
    self.push(context)
    return self
