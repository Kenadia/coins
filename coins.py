"""Query account balances from multiple cryptocurrency exchanges.

Configuration:
  Behavior can be configured via variables set in config.py. The options are
below. All are optional, but the script will do nothing if EXCHANGES is not
provided:
  - EXCHANGES: A list of modules implementing the exchange API (see below).
  - SYMOL_TRANSFORM: Used to specify a mapping for correcting currency symbols.
  - CACHE_FILE: Where to store the cache. Defaults to `balances.pickle`.
  - `TOTAL_COLUMN`: The label for the column containing balance totals. Defaults
        to 'Subtotal'.
  - `EXCLUDE_ZEROS`: Whether to exclude zero balances. Defaults to `True`.

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

try:
  import config
except ImportError:
  print 'Warning: Please add a `config.py` file in order to use this script.\n'
  config = object()

# Global variable storing the cached balances.
CACHE = {}

CACHE_FILE = getattr(config, 'CACHE_FILE', 'balances.pickle')
TOTAL_COLUMN = getattr(config, 'TOTAL_COLUMN', 'Subtotal')


def read_cache():
  """Read from cache file into the global CACHE variable."""
  if not os.path.exists(CACHE_FILE):
    return
  print 'Reading previous data from `%s`.\n' % CACHE_FILE
  with open(CACHE_FILE, 'r') as f:
    CACHE.update(pickle.load(f))


def write_cache():
  """Write from the global CACHE variable to the cache file."""
  with open(CACHE_FILE, 'w') as f:
    pickle.dump(CACHE, f)


def get_exchange_modules():
  """Import the configured modules and return them as a list."""
  module_names = getattr(config, 'EXCHANGES', [])
  return [importlib.import_module('exchanges.' + name) for name in module_names]


def get_balances(exchange):
  """Get balances either from the cache or by making a query."""

  # Get the exchange short name (e.g. 'polo', 'trex', 'cb').
  short_name = exchange.__name__.rpartition('.')[2]

  if (short_name not in CACHE or
      len(sys.argv) > 1 and short_name in sys.argv[1].split(',')):
    print 'Making request to %s API.' % exchange.NAME
    CACHE[short_name] = exchange.get_balances()
    write_cache()
  return CACHE[short_name]


def get_data():
  """Acquire all data and transform it for output to a CSV.

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

  for exchange in get_exchange_modules():
    exchange_name = exchange.NAME
    balances = get_balances(exchange)
    for currency, amount in balances.iteritems():
      data[currency][exchange_name] = amount
      data[currency][TOTAL_COLUMN] += amount
    columns.append(exchange_name)

  # Sort the exchanges alphabetically.
  columns.sort()

  columns.append(TOTAL_COLUMN)
  return data, columns


def main():
  """Retrieve account balances and save a data table to the clipboard."""
  if not (len(sys.argv) > 1 and sys.argv[1] == 'all'):
    read_cache()

  # Prepare a writer to write a CSV file to a string. We use a tab delimiter to
  # make it easy to paste the data into a spreadsheet application.
  out = io.BytesIO()
  writer = csv.writer(out, delimiter='\t')
  data, columns = get_data()

  # Write the header row.
  writer.writerow(['Currency'] + columns)

  # Sort the rows alphabetically by the currency symbol.
  currencies = sorted(data.iterkeys())

  zero_count = 0

  for currency in currencies:
    balances = data[currency]

    # Count zero-balances and skip, depending on the config.
    if balances[TOTAL_COLUMN] == 0:
      zero_count += 1
      if getattr(config, 'EXCLUDE_ZEROS', True):
        continue

    amounts = [balances[column] for column in columns]

    # Apply symbol transformations.
    symbol_map = getattr(config, 'SYMBOL_TRANSFORM', {})
    if currency in symbol_map:
      current = symbol_map[currency]

    writer.writerow([currency] + amounts)

  try:
    print ('\nRetrieved balances for %d currencies (%d with balances) from '
           '%d exchanges.\n' %
           (len(currencies), len(currencies) - zero_count, len(amounts) - 1))
  except NameError:
    print 'No data was retrieved. Please configure `EXCHANGES` in config.py.\n'

  raw_input('Export ready. Press enter to save to clipboard.')
  pyperclip.copy(out.getvalue())
  print


if __name__ == '__main__':
  main()
