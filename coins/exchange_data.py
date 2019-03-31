"""Query and aggregate account balances from multiple cryptocurrency exchanges.

# Configuration

The Exchanges class requires a `config` parameter, which can be, e.g., a module
or a dictionary. The following keys are used, but only `EXCHANGE_KEYS` is
required:
  - EXCHANGE_KEYS: Dictionary of API credentials, keyed on exchange module name.
  - SYMBOL_TRANSFORM: Used to specify a mapping for correcting currency symbols.
  - EXCLUDE_ZEROS: Whether to exclude zero balances. Defaults to `True`.
  - REQUIRED_ROWS: A list of currency symbols to always include.

# Caching

By default, responses returned by the exchange APIs are cached in a file named
`balances.pickle.` This is configurable via the `cache` parameter.

# Exchange modules

The code for querying each exchange is separated into separate Python modules.
The modules should contain the minimum code required to do the job. Each must
provide the following API:
  - NAME: A string representing the full exchange name.
  - get_balances(api_config): Returns account balances as a dictionary from
    symbol (e.g. 'BTC', 'ETH') to amount, as a float.
"""

from __future__ import print_function

import collections
import csv
import importlib
import io
import traceback

import frozendict

DEFAULT_CACHE = 'balances.pickle'


def print_error_with_traceback(_error):
  traceback.print_exc()


class Exchanges(object):
  CONFIG_DEFAULTS = {
      'EXCHANGE_KEYS': frozendict.frozendict(),
      'EXCLUDE_ZEROS': True,
      'REQUIRED_ROWS': (),
      'SYMBOL_TRANSFORM': frozendict.frozendict(),
  }
  EXCHANGES_MODULE_BASE = 'coins.exchanges'

  def __init__(self, config, cache=None):
    if not isinstance(config, dict):
      config = config.__dict__

    if cache is None or cache is True:
      cache = coins.cache.Cache(DEFAULT_CACHE)
    elif cache is False:
      cache = coins.cache.NoCache()

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
      module_config = self.config['EXCHANGE_KEYS'][module_name]
      balances = exchange_module.get_balances(module_config)

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

  def get_table(self, module_names, handle_error=print_error_with_traceback):
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
