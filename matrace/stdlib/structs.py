from matrace.utils.dict_wrapper import DictWrapper


def create_struct(*args, **kwargs):
  d = {**kwargs}
  for i in range(0, len(args), 2):
    assert isinstance(args[i], str)
    d[args[i]] = args[i + 1]
  return DictWrapper(d)
