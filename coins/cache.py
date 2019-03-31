import os
import pickle


class Cache(object):

  def __init__(self, cache_file, ignore_cache_for=()):
    self.cache_file = cache_file
    self.ignore_cache_for = ignore_cache_for

  def _read(self):
    """Read the whole cache."""
    if not os.path.exists(self.cache_file):
      return {}
    with open(self.cache_file, 'rb') as f:
      return pickle.load(f)

  def read(self, key):
    """Read from the cache file and return the data for a given module."""
    if key in self.ignore_cache_for:
      return
    data = self._read()
    return data.get(key)

  def write(self, key, value):
    """Write to the cache file."""
    data = self._read()
    data[key] = value
    with open(self.cache_file, 'wb') as f:
      pickle.dump(data, f)
