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

import collections
import csv
import importlib
import io
import os
import pickle
import sys

import pyperclip

import cmc
try:
  import config
except ImportError:
  print 'Warning: Please add a `config.py` file in order to use this script.\n'
  config = object()

CACHE_FILE = getattr(config, 'CACHE_FILE', 'balances.pickle')
TOTAL_COLUMN = getattr(config, 'TOTAL_COLUMN', 'Subtotal')

EXCHANGES_MODULE_BASE = 'coins.exchanges'


def read_cache():
  """Read from the cache file and return the contents."""
  if not os.path.exists(CACHE_FILE):
    return
  print 'Reading previous data from `%s`.\n' % CACHE_FILE
  with open(CACHE_FILE, 'r') as f:
    return pickle.load(f)


def write_cache(cache):
  """Write to the cache file."""
  with open(CACHE_FILE, 'w') as f:
    pickle.dump(cache, f)


def get_exchange_modules():
  """Import the configured modules and return them as a list."""
  module_names = getattr(config, 'EXCHANGES', [])
  return [
      importlib.import_module('{}.{}'.format(EXCHANGES_MODULE_BASE, name))
      for name in module_names
  ]


def get_balances(exchange_module, cache, ignore_cache):
  """Get balances either from the cache or by making a query."""

  # Get the exchange short name (e.g. 'polo', 'trex', 'cb').
  short_name = exchange_module.__name__.rpartition('.')[2]

  if short_name not in cache or ignore_cache:
    print 'Making request to %s API.' % exchange_module.NAME
    cache[short_name] = exchange_module.get_balances()
    write_cache(cache)
  return cache[short_name]


def get_data(cache=None, ignore_cache_for=()):
  """Acquire all data and transform it for output to a CSV.

  Args:
    cache: A dictionary of results read from the cache, or None.
    ignore_cache_for: A list of exchange names for which to ignore the cache.

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
  if cache is None:
    cache = {}

  data = collections.defaultdict(lambda: collections.defaultdict(int))
  columns = []

  for exchange_module in get_exchange_modules():
    exchange_name = exchange_module.NAME
    ignore_cache = exchange_name in ignore_cache_for
    try:
      balances = get_balances(exchange_module, cache, ignore_cache)
    except Exception as e:
      print 'Error: %s' % e
      continue
    for currency, amount in balances.iteritems():
      data[currency][exchange_name] = amount
      data[currency][TOTAL_COLUMN] += amount
    columns.append(exchange_name)

  # Sort the exchanges alphabetically.
  columns.sort()

  columns.append(TOTAL_COLUMN)
  return data, columns


def write_csv(data, columns, exclude_zeros, required_rows=None,
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
    if balances[TOTAL_COLUMN] == 0:
      zero_count += 1
      if (exclude_zeros and currency not in required_rows):
        continue

    amounts = [balances[column] for column in columns]

    # Apply symbol transformations.
    if currency in symbol_map:
      currency = symbol_map[currency]

    writer.writerow([currency] + amounts)

  try:
    print ('\nRetrieved balances for %d currencies (%d with balances) from '
           '%d exchanges.\n' %
           (len(currencies), len(currencies) - zero_count, len(amounts) - 1))
  except NameError:
    print 'No data was retrieved. Please configure `EXCHANGES` in config.py.\n'
  return out.getvalue()


def main():
  """Retrieve account balances and save a data table to the clipboard."""
  ignore_cache_for = []

  if len(sys.argv) == 1:
    # No argument: Use the cache for all exchanges.
    cache = read_cache()
  elif sys.argv[1] == 'all':
    # Argument is `all`: Ignore the cache for all exchanges.
    cache = {}
  else:
    # Otherwise: Ignore the cache for the specified exchanges.
    cache = read_cache()
    short_names = sys.argv[1].split(',')
    for exchange_module in get_exchange_modules():
      short_name = exchange_module.__name__.rpartition('.')[2]
      if short_name in short_names:
        ignore_cache_for.append(exchange_module.NAME)

  data, columns = get_data(cache, ignore_cache_for)

  # Apply symbol mapping and remove unnecessary rows.
  exclude_zeros = getattr(config, 'EXCLUDE_ZEROS', True)
  required_rows = getattr(config, 'REQUIRED_ROWS', [])
  symbol_map = getattr(config, 'SYMBOL_TRANSFORM', {})
  data = {
      symbol_map.get(symbol, symbol): balances
      for symbol, balances in data.iteritems()
      if (not exclude_zeros or
          symbol in required_rows or
          any(amount for amount in balances.itervalues()))
  }

  # Calculate USD totals.
  totals = collections.defaultdict(int)
  quotes = cmc.get_quotes(data.iterkeys())
  for symbol, balances in data.iteritems():
    for exchange_name, amount in balances.iteritems():
      totals[exchange_name] += amount * quotes[symbol]

  totals.pop('Subtotal')

  for exchange_name, usd_total in totals.iteritems():
    print '% 15s: %.2f' % (exchange_name, usd_total)
  print
  print '% 15s: %.2f' % ('TOTAL', sum(totals.itervalues()))

  # csv_string = write_csv(data, columns, exclude_zeros, required_rows,
  #                        symbol_map, delimiter='\t')

  # raw_input('Export ready. Press enter to save to clipboard.')
  # pyperclip.copy(csv_string)
  # print


if __name__ == '__main__':
  main()
