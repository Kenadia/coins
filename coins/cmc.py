import json

import requests

from coins import config

BASE_URL = 'https://pro-api.coinmarketcap.com/v1/'
LISTINGS_URL = 'cryptocurrency/listings/latest'
QUOTES_URL = 'cryptocurrency/quotes/latest'

headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': config.COINMARKETCAP_KEY,
}
session = requests.Session()
session.headers.update(headers)


def _get(endpoint, payload):
  try:
    raw_response = session.get(BASE_URL + endpoint, params=payload)
  except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
          requests.exceptions.TooManyRedirects) as e:
    # TODO: ?
    # E.g. Exception: CoinMarketCap error: Invalid value for "symbol": "XML"
    raise
  response = json.loads(raw_response.text)
  error = response['status']['error_message']
  if error is not None:
    raise Exception('CoinMarketCap error: {}'.format(error))
  return response['data']


def get_listings():
  payload = {
      'start': '1',
      'limit': '5000',
      'convert': 'USD',
  }
  return _get(LISTINGS_URL, payload)


def get_quotes(symbols):
  payload = {
      'convert': 'USD',
      'symbol': ','.join(s for s in symbols if s != 'USD'),
  }
  data = _get(QUOTES_URL, payload)

  # Return simplified data.
  return {
      symbol: data[symbol]['quote']['USD']['price']
      for symbol in data.iterkeys()
  }
