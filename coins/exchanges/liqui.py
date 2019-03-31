from __future__ import print_function

import hashlib
import hmac
import time
import urllib

import requests

NAME = 'Liqui'
URL = 'https://api.liqui.io/tapi'


def get_balances(api_creds):
  params = {
      'method': 'getInfo',
      'nonce': int(time.time()),
  }
  params_string = urllib.parse.urlencode(params)
  signature = hmac.new(
      api_creds['secret'].encode(), params_string.encode(), hashlib.sha512
  ).hexdigest()
  headers = {
      'Key': api_creds['key'],
      'Sign': signature,
  }
  data = requests.post(URL, data=params, headers=headers).json()

  if 'error' in data:
    raise RuntimeError('Request failed: %s' % data['error'])

  result = data['return']['funds']
  return {
      currency.upper(): float(balance)
      for currency, balance in result.items()
  }


if __name__ == '__main__':
  balances = get_balances(api_creds)
  for symbol, balance in balances.items():
    if balance > 0:
      print('%6s %.3f' % (symbol, balance))
