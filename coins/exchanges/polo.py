from __future__ import print_function

import hashlib
import hmac
import time
import urllib

import requests

from coins import config

NAME = 'Poloniex'
URL = 'https://poloniex.com/tradingApi'


def get_balances():
  data = {
      'command': 'returnBalances',
      'nonce': int(time.time() * 1000),
  }
  post_data = urllib.parse.urlencode(data).encode('ascii')
  signature = hmac.new(
      config.POLO_SECRET.encode('ascii'), post_data, hashlib.sha512).hexdigest()
  headers = {
      'Key': config.POLO_KEY,
      'Sign': signature,
  }
  data = requests.post(URL, data, headers=headers).json()
  balances = {str(key): float(value) for key, value in data.items()}
  return balances


if __name__ == '__main__':
  balances = get_balances()
  for symbol, balance in balances.items():
    if balance > 0:
      print('%6s %.3f' % (symbol, balance))
