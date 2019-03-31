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

import pyperclip

from coins import cmc

EXCHANGES_MODULE_BASE = 'coins.exchanges'


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

  def read(self, module_name):
    """Read from the cache file and return the data for a given module."""
    if module_name in self.ignore_cache_for:
      return
    data = self._read()
    return data.get(module_name)

  def write(self, module_name, exchange_data):
    """Write to the cache file."""
    data = self._read()
    data[module_name] = exchange_data
    with open(self.cache_file, 'wb') as f:
      pickle.dump(data, f)


def get_exchange_module(module_name):
  return importlib.import_module('{}.{}'.format(EXCHANGES_MODULE_BASE, module_name))


def get_balances(module_name, exchange_module, cache):
  """Get balances either from the cache or by making a query."""
  exchange_name = exchange_module.NAME
  exchange_data = cache.read(module_name)

  if exchange_data is not None:
    print('Reading cached data for exchange {}.'.format(exchange_name))

  else:
    print('Making request to {} API.'.format(exchange_name))
    exchange_data = exchange_module.get_balances()
    cache.write(module_name, exchange_data)

  return exchange_data


def get_data(module_names, config, cache=None):
  """Acquire all data and transform it for output to a CSV.

  Args:
    cache: Cache object.

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
  total_column = getattr(config, 'TOTAL_COLUMN', 'Subtotal')

  data = collections.defaultdict(lambda: collections.defaultdict(int))
  columns = []

  for module_name in module_names:
    exchange_module = get_exchange_module(module_name)
    exchange_name = exchange_module.NAME
    try:
      balances = get_balances(module_name, exchange_module, cache)
    except Exception as e:
      traceback.print_exc()
      continue
    for currency, amount in balances.items():
      data[currency][exchange_name] = amount
      data[currency][total_column] += amount
    columns.append(exchange_name)

  # Sort the exchanges alphabetically.
  columns.sort()
  columns.append(total_column)

  # Apply symbol mapping and remove unnecessary rows.
  exclude_zeros = getattr(config, 'EXCLUDE_ZEROS', True)
  required_rows = getattr(config, 'REQUIRED_ROWS', [])
  symbol_map = getattr(config, 'SYMBOL_TRANSFORM', {})
  data = {
      symbol_map.get(symbol, symbol): balances
      for symbol, balances in data.items()
      if (not exclude_zeros or
          symbol in required_rows or
          any(amount for amount in balances.values()))
  }

  return data, columns


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

  # Read config from config.py.
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
  data, columns = get_data(module_names, config, cache)

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
  usd_by_exchange.pop('Subtotal')

  # Calculate USD totals by token.
  usd_by_token = {
      symbol: balances['Subtotal'] * quotes[symbol]
      for symbol, balances in data.items()
  }

  high_value_token_counts = (
      (symbol, balances['Subtotal'])
      for symbol, balances in data.items()
      if usd_by_token[symbol] >= 500.0
  )

  mid_value_token_counts = (
      (symbol, balances['Subtotal'])
      for symbol, balances in data.items()
      if usd_by_token[symbol] >= 20.0 and usd_by_token[symbol] < 500.0
  )

  low_value_token_counts = (
      (symbol, balances['Subtotal'])
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
