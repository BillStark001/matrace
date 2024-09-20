import pickle
import os
from functools import wraps


USE_CACHE = object()


def cache(cache_file='func_cache.pkl'):
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      if args and args[0] is USE_CACHE:
        # try load
        if os.path.exists(cache_file):
          try:
            # first try using cache
            with open(cache_file, 'rb') as f:
              args, kwargs = pickle.load(f)
            return func(*args, **kwargs)
          except (pickle.PickleError, EOFError, FileNotFoundError) as e:
            # do nothing if failed
            return None
        else:
          # cache file inexistent
          return None
      else:  # execute normally and cache args
        try:
          with open(cache_file, 'wb') as f:
            pickle.dump((args, kwargs), f)
        except (pickle.PickleError, IOError) as e:
          pass  # do nothing
        result = func(*args, **kwargs)
        return result
    return wrapper
  return decorator
