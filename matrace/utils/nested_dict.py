from typing import TypeVar, Generic, Dict, Any, Optional, Callable, Tuple
from weakref import WeakSet

K = TypeVar('K')
V = TypeVar('V')


class NestedDict(Generic[K, V]):
  def __init__(
      self,
      parent: Optional['NestedDict[K, V]'] = None,
      default: Optional[V] = None,
      default_none: bool = False,
      default_factory: Optional[Callable[[], V]] = None,
  ):
    self._data: Dict[K, V] = {}
    self._cache: Dict[K, V] = {}
    self._parent = parent
    self._children: WeakSet['NestedDict[K, V]'] = WeakSet()

    self._default = default
    self._default_none = default_none
    self._default_factory = default_factory

  @property
  def parent(self):
    return self._parent

  def create_default_value(self) -> Tuple[bool, V]:
    if self._default is not None:
      return True, self._default
    elif self._default_factory is not None:
      return True, self._default_factory()
    elif self._default_none:
      return True, None
    else:
      return False, None

  def __getitem__(self, key: K) -> V:
    # Check cache first
    if key in self._cache:
      return self._cache[key]

    # Check local data
    if key in self._data:
      self._cache[key] = self._data[key]
      return self._data[key]

    # Check parent recursively
    if self._parent:
      value = self._parent[key]
      self._cache[key] = value
      return value

    has_default, val = self.create_default_value()
    if has_default:
      self._data[key] = val
      self.invalidate_cache(key)
      return val

    raise KeyError(key)

  def __setitem__(self, key: K, value: V) -> None:
    self._data[key] = value
    self.invalidate_cache(key)

  def __contains__(self, key: K) -> bool:
    return key in self._cache \
        or key in self._data \
        or (self._parent is not None and key in self._parent)

  def invalidate_cache(self, key: K) -> None:
    # Clear local cache for the key
    if key in self._cache:
      del self._cache[key]

    # Notify listeners
    for child in list(self._children):
      child.invalidate_cache(key)

  def create_child(self) -> 'NestedDict[K, V]':
    child = NestedDict(
        parent=self,
        default=self._default,
        default_none=self._default_none,
        default_factory=self._default_factory,
    )
    self._children.add(child)
    return child

  def get(self, key: K, default: Any = None) -> Any:
    try:
      return self[key]
    except KeyError:
      return default


# Example usage
if __name__ == "__main__":
  # Create root dictionary
  root = NestedDict[str, int]()
  root["a"] = 1
  root["b"] = 2

  # Create child dictionary
  child1 = root.create_child()
  child1["d"] = 3
  child1["c"] = 4

  # Create grandchild dictionary
  grandchild = child1.create_child()
  grandchild["c"] = 5

  # Test lookups
  print(grandchild["a"])  # Output: 1 (from root)
  print(grandchild["b"])  # Output: 3 (from child1)
  print(grandchild["c"])  # Output: 5 (from grandchild)

  # Test cache invalidation
  def on_change():
    print("Value changed!")

  root["b"] = 10  # This will trigger the listener and invalidate caches

  print(grandchild["b"])  # Output: 10 (updated value from root)
