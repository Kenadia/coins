"""Query account balances from multiple cryptocurrency exchanges.

Configuration:
  Behavior can be configured via variables set in config.py. The options are
below. All are optional, but the script will do nothing if EXCHANGES is not
provided:
  - EXCHANGES: A list of modules implementing the exchange API (see below).
  - SYMBOL_TRANSFORM: Used to specify a mapping for correcting currency symbols.
  - CACHE_FILE: Where to store the cache. Defaults to `balances.pickle`.
  - TOTAL_COLUMN: The label for the column containing balance totals. Defaults
        to 'Subtotal'.
  - EXCLUDE_ZEROS: Whether to exclude zero balances. Defaults to `True`.
  - REQUIRED_ROWS: A list of currency symbols to always include.

Caching:
  By default, results are cached, in order to avoid unnecessary querying. An
argument should be provided if you wish to override the cache, for example:

    python coins.py polo,trex  # Ignore the cache for specific exchanges.
    python coins.py all        # Ignore the cache entirely.

Exchange modules and API:
  The code for querying each exchange is separated into separate Python modules.
The modules should contain the minimum code required to do the job. Each must
provide the following API:
  - NAME: A string representing the full exchange name.
  - get_balances(): A function which will query and return account balances as a
        dictionary from currency (e.g. 'BTC', 'ETH') to an amount, as a float.
        Zero balances are not expected to be filtered out by this function.

Credentials:
  As a convention, API credentials are stored in config.py under the variables
`{SHORT_NAME}_KEY` and `{SHORT_NAME}_SECRET` for each exchange.
"""

from __future__ import print_function

import collections
import csv
import importlib
import io
import os
import pickle
import sys
import traceback

import frozendict
import pyperclip

from coins import cmc


class Cache(object):

  def __init__(self, cache_file, ignore_cache_for):
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


class Exchanges(object):
  CONFIG_DEFAULTS = {
      'EXCLUDE_ZEROS': True,
      'REQUIRED_ROWS': (),
      'SYMBOL_TRANSFORM': frozendict.frozendict(),
  }
  EXCHANGES_MODULE_BASE = 'coins.exchanges'

  def __init__(self, config, cache):
    if not isinstance(config, dict):
      config = config.__dict__

    self.config = dict(self.CONFIG_DEFAULTS, **config)
    self.cache = cache

  def _get_exchange_module(self, module_name):
    return importlib.import_module(
        '{}.{}'.format(self.EXCHANGES_MODULE_BASE, module_name)
    )

  def get_data(self, module_name):
    """Get balances for an exchange.

    Returns:

      Balances, as follows:

          {
              'Poloniex': {
                  'BTC': 1.0,
                  'ETH': 2.0,
                  'XRP': 0.0,
              }
          }
    """
    exchange_module = self._get_exchange_module(module_name)
    exchange_name = exchange_module.NAME
    exchange_data = self.cache.read(module_name)

    if exchange_data is not None:
      print('Using cached data for exchange {}.'.format(exchange_name))

    else:
      print('Making request to {} API.'.format(exchange_name))
      balances = exchange_module.get_balances()

      # Apply transformations, according to the configuration.
      balances = {
          self.config['SYMBOL_TRANSFORM'].get(symbol, symbol): balance
          for symbol, balance in balances.items()
          if (not self.config['EXCLUDE_ZEROS'] or
              symbol in self.config['REQUIRED_ROWS'] or
              balance)
      }

      exchange_data = { exchange_name: balances }
      self.cache.write(module_name, exchange_data)

    return exchange_data

  @staticmethod
  def merge_data(exchange_balances, total_column='Total'):
    """Merge data from multiple exchanges and calculate totals by symbol.

    Returns:
      Account balances, in a format like the following:

          {
              'BTC': {
                  'Poloniex': 1.0,
                  'GDAX': 2.0,
                  'Bittrex': 0.0,
              },
              'ETH': {
                  'Poloniex': 0.0,
                  'GDAX': 1.0,
                  'Bittrex': 1.0,
              },
          }
    """
    data = collections.defaultdict(lambda: collections.defaultdict(int))
    columns = []

    for exchange_data in exchange_balances:
      assert len(exchange_data) == 1
      exchange_name = list(exchange_data.keys())[0]
      balances = exchange_data[exchange_name]

      for currency, amount in balances.items():
        data[currency][exchange_name] = amount
        data[currency][total_column] += amount
      columns.append(exchange_name)

    # Sort the exchange names alphabetically.
    columns.sort()
    columns.append(total_column)
    return data, columns

  def get_table(self, module_names, handle_error):
    results = []

    for name in module_names:
      try:
        data = self.get_data(name)
      except Exception as e:
        handle_error(e)
      else:
        results.append(data)

    return Exchanges.merge_data(results)


def write_csv(data, columns, total_column, exclude_zeros, required_rows=None,
              symbol_map=None, delimiter=','):
  required_rows = required_rows or []
  symbol_map = symbol_map or {}

  # Prepare a writer to write a CSV file to a string. We use a tab delimiter to
  # make it easy to paste the data into a spreadsheet application.
  out = io.BytesIO()
  writer = csv.writer(out, delimiter=delimiter)

  # Write the header row.
  writer.writerow(['Currency'] + columns)

  # Sort the rows alphabetically by the currency symbol.
  currencies = sorted(set(data.keys() + required_rows))

  zero_count = 0

  for currency in currencies:
    balances = data[currency]

    # Count zero-balances and skip, depending on the config.
    if balances[total_column] == 0:
      zero_count += 1
      if (exclude_zeros and currency not in required_rows):
        continue

    amounts = [balances[column] for column in columns]

    # Apply symbol transformations.
    if currency in symbol_map:
      currency = symbol_map[currency]

    writer.writerow([currency] + amounts)

  try:
    print('\nRetrieved balances for %d currencies (%d with balances) from '
           '%d exchanges.\n' %
           (len(currencies), len(currencies) - zero_count, len(amounts) - 1))
  except NameError:
    print('No data was retrieved. Please configure `EXCHANGES` in config.py.\n')
  return out.getvalue()


def main():
  """Retrieve account balances and save a data table to the clipboard."""

  # Read config from coins/config.py.
  try:
    from coins import config
  except ImportError:
    print('Warning: Please add a `config.py` file in order to use this script.\n')
    config = object()

  module_names = getattr(config, 'EXCHANGES', [])

  # No argument: Use the cache for all exchanges.
  if len(sys.argv) == 1:
    ignore_cache_for = []

  # Argument is `all`: Ignore the cache for all exchanges.
  elif sys.argv[1] == 'all':
    ignore_cache_for = module_names

  # Otherwise: Ignore the cache for the specified exchanges.
  else:
    ignore_cache_for = sys.argv[1].split(',')

  CACHE_FILE = getattr(config, 'CACHE_FILE', 'balances.pickle')
  cache = Cache(CACHE_FILE, ignore_cache_for)

  exchanges = Exchanges(config, cache)

  def handle_error(_error):
    traceback.print_exc()

  data, columns = exchanges.get_table(module_names, handle_error)

  # Calculate USD totals by exchange.
  usd_by_exchange = collections.defaultdict(int)
  symbols = data.keys()

  if not symbols:
    print('Cannot continue: did not find any balances.')
    sys.exit(1)

  quotes = cmc.get_quotes(symbols)
  for symbol, balances in data.items():
    for exchange_name, amount in balances.items():
      usd_by_exchange[exchange_name] += amount * quotes[symbol]
  usd_by_exchange.pop('Total')

  # Calculate USD totals by token.
  usd_by_token = {
      symbol: balances['Total'] * quotes[symbol]
      for symbol, balances in data.items()
  }

  high_value_token_counts = (
      (symbol, balances['Total'])
      for symbol, balances in data.items()
      if usd_by_token[symbol] >= 500.0
  )

  mid_value_token_counts = (
      (symbol, balances['Total'])
      for symbol, balances in data.items()
      if usd_by_token[symbol] >= 20.0 and usd_by_token[symbol] < 500.0
  )

  low_value_token_counts = (
      (symbol, balances['Total'])
      for symbol, balances in data.items()
      if usd_by_token[symbol] < 20.0
  )

  # Print token counts.
  print('HIGH VALUE')
  for symbol, balance in sorted(high_value_token_counts):
    print('% 15s: % 11.2f = $% 9.2f' % (symbol, balance, usd_by_token[symbol]))
  print()
  print('MID VALUE')
  for symbol, balance in sorted(mid_value_token_counts):
    print('% 15s: % 11.2f = $% 9.2f' % (symbol, balance, usd_by_token[symbol]))
  print()
  print('LOW VALUE')
  for symbol, balance in sorted(low_value_token_counts):
    print('% 15s: % 11.2f = $% 9.2f' % (symbol, balance, usd_by_token[symbol]))
  print()

  print()

  for exchange_name, usd_total in usd_by_exchange.items():
    print('% 15s: %.2f' % (exchange_name, usd_total))
  print()
  print('% 15s: %.2f' % ('TOTAL', sum(usd_by_exchange.values())))

  # csv_string = write_csv(data, columns, total_column, exclude_zeros, required_rows,
  #                        symbol_map, delimiter='\t')

  # raw_input('Export ready. Press enter to save to clipboard.')
  # pyperclip.copy(csv_string)
  # print()


if __name__ == '__main__':
  main()
