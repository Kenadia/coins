'''Query and aggregate account balances from multiple cryptocurrency exchanges.

See example_config.py and coins/exchange_data.py for info on configuration.

Usage:
  python main.py            # Use the cache for all exchanges.
  python main.py polo,trex  # Ignore the cache for specific exchanges.
  python main.py all        # Ignore the cache entirely.
'''

import collections
import sys

import coins

# Read config from config.py.
try:
  import config
except ImportError:
  print('Please add a `config.py` file in order to use this script.\n')
  sys.exit(1)


def parse_args():
  # No argument: Use the cache for all exchanges.
  if len(sys.argv) == 1:
    ignore_cache_for = []

  # Argument is `all`: Ignore the cache for all exchanges.
  elif sys.argv[1] == 'all':
    ignore_cache_for = module_names

  # Otherwise: Ignore the cache for the specified exchanges.
  else:
    ignore_cache_for = sys.argv[1].split(',')
  return ignore_cache_for


def main():
  """Retrieve account balances and save a data table to the clipboard."""
  CACHE_FILE = getattr(config, 'CACHE_FILE', coins.exchange_data.DEFAULT_CACHE)
  module_names = getattr(config, 'EXCHANGES', [])

  ignore_cache_for = parse_args()
  cache = coins.cache.Cache(CACHE_FILE, ignore_cache_for)
  exchanges = coins.Exchanges(config, cache)
  data, columns = exchanges.get_table(module_names)

  # Calculate USD totals by exchange.
  usd_by_exchange = collections.defaultdict(int)
  symbols = data.keys()

  if not symbols:
    print('Cannot continue: did not find any balances.')
    sys.exit(1)

  quotes = coins.CMC(config).get_quotes(symbols)
  for symbol, balances in data.items():
    for exchange_name, amount in balances.items():
      usd_by_exchange[exchange_name] += amount * quotes.get(symbol, 0)
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
