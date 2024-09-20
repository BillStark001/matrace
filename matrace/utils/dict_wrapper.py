

class DictWrapper:

  _data: dict

  def __init__(self, data):
    if not isinstance(data, dict):
      raise ValueError("Input must be a dictionary.")
    super().__setattr__('_data', data)

  def __getitem__(self, key):
    value = self._data[key]
    if isinstance(value, dict):
      return DictWrapper(value)
    return value

  def __setitem__(self, key, value):
    if isinstance(value, DictWrapper):
      value = value._data
    self._data[key] = value

  def __getattr__(self, key):
    try:
      value = self._data[key]
    except KeyError:
      raise AttributeError(f"'DictWrapper' object has no attribute '{key}'")
    if isinstance(value, dict):
      return DictWrapper(value)
    return value

  def __setattr__(self, key, value):
    if key == '_data':
      super().__setattr__(key, value)
      return
    if isinstance(value, DictWrapper):
      value = value._data
    self._data[key] = value

  def __repr__(self):
    return f"DictWrapper({self._data})"

  def __hash__(self) -> int:
    return hash(self._data)

  def __eq__(self, other):
    return isinstance(other, DictWrapper) and self._data == other._data
