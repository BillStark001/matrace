from matrace.utils.dict_wrapper import DictWrapper


def create_struct(*args, **kwargs):
  d = {**kwargs}
  for i in range(0, len(args), 2):
    if not isinstance(args[i], str):
      raise TypeError(
          f'create_struct: field names must be strings, '
          f'got {type(args[i]).__name__!r} at positional argument {i}.'
      )
    d[args[i]] = args[i + 1]
  return DictWrapper(d)
