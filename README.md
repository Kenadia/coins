# coins

A script for querying your account balances from multiple cryptocurrency
exchanges. It produces a data table that can be easily pasted into a spreadsheet
application.

Usage:

```
python coins.py
```

Example output:

![Screenshot of example output.](https://github.com/Kenadia/coins/blob/master/example_output.png?raw=true)

## Configuration

Behavior can be configured via variables set in `config.py`. The options are
below. All are optional, but the script will do nothing if `EXCHANGES` is not
provided:
- `EXCHANGES`: A list of modules implementing the exchange API (see below).
- `SYMBOL_TRANSFORM`: Used to specify a mapping for correcting currency symbols.
- `CACHE_FILE`: Where to store the cache. Defaults to `balances.pickle`.
- `TOTAL_COLUMN`: The label for the column containing balance totals.
       Defaults to 'Subtotal'.
- `EXCLUDE_ZEROS`: Whether to exclude zero balances. Defaults to `True`.

## Caching

By default, results are cached, in order to avoid unnecessary querying. An
argument should be provided if you wish to override the cache, for example:

```
python coins.py polo,trex  # Ignore the cache for specific exchanges.
python coins.py all        # Ignore the cache entirely.
```

## Exchange modules and API

The code for querying each exchange is separated into separate Python modules.
Code is provided for querying several popular exchanges. You can provide your
own modules if you want to query other exchanges.

The modules should contain the minimum code required to do the job. Each must
provide the following API:
- `NAME`: A string representing the full exchange name.
- `get_balances()`: A function which will query and return account balances as a
    dictionary from currency (e.g. 'BTC', 'ETH') to an amount, as a float.
    Zero balances are not expected to be filtered out by this function.

## Authentication

As a convention, API credentials are stored in config.py under the variables
`{SHORT_NAME}_KEY` and `{SHORT_NAME}_SECRET` for each exchange.

It is recommended that you give the API keys the minimum permissions required to
query account balances.
