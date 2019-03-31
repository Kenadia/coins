import json

import requests


class CoinMarketCapError(Exception):

  def __init__(self, message):
    self.error_message = message
    super(CoinMarketCapError, self).__init__(
        'CoinMarketCap error: {}'.format(message),
    )


class CMC(object):
  BASE_URL = 'https://pro-api.coinmarketcap.com/v1/'
  LISTINGS_URL = 'cryptocurrency/listings/latest'
  QUOTES_URL = 'cryptocurrency/quotes/latest'
  SYMBOL_ERROR = 'Invalid values for "symbol": '

  def __init__(self, config):
    if not isinstance(config, dict):
      config = config.__dict__

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': config['COINMARKETCAP_KEY'],
    }
    self._session = requests.Session()
    self._session.headers.update(headers)

  def _get(self, endpoint, payload):
    try:
      raw_response = self._session.get(self.BASE_URL + endpoint, params=payload)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects) as e:
      # TODO: ?
      raise
    response = json.loads(raw_response.text)
    error = response['status']['error_message']
    if error is not None:
      raise CoinMarketCapError(error)
    return response['data']

  def get_listings(self, ):
    payload = {
        'start': '1',
        'limit': '5000',
        'convert': 'USD',
    }
    return self._get(self.LISTINGS_URL, payload)

  def get_quotes(self, symbols):
    symbols = list(symbols)

    def payload(symbols):
      return {
          'convert': 'USD',
          'symbol': ','.join(s for s in symbols if s != 'USD'),
      }

    invalid_symbols = None

    try:
      data = self._get(self.QUOTES_URL, payload(symbols))
    except CoinMarketCapError as error:
      message = error.error_message
      if self.SYMBOL_ERROR not in message:
        raise

      # Should be something like '"BTV,CODY,EXTRA,LV,WHC"'.
      error_value = message[len(self.SYMBOL_ERROR):]

      # Remove the invalid symbols.
      invalid_symbols = error_value[1:-1].split(',')
      for s in invalid_symbols:
        symbols.remove(s)
      data = self._get(self.QUOTES_URL, payload(symbols))

    # Return simplified data.
    quotes = {
        symbol: data[symbol]['quote']['USD']['price']
        for symbol in data.keys()
    }

    if invalid_symbols:
      quotes.update({ symbol: 0 for symbol in invalid_symbols })
      print ('Warning: CoinMarketCap does not recognize the following symbols '
             '["{}"]'.format('", "'.join(invalid_symbols)))

    # The CMC API sometimes won't return data even for recognized symbols.
    quotes.setdefault('USD', 1.0)
    missing_symbols = set(symbols) - set(quotes)

    if missing_symbols:
      quotes.update({ symbol: 0 for symbol in missing_symbols })
      print ('Warning: CoinMarketCap did not return quotes for the following '
             'symbols ["{}"]'.format('", "'.join(missing_symbols)))

    return quotes
