import hashlib
import hmac
import time
import urllib

import requests

from coins import config

NAME = 'Liqui'
URL = 'https://api.liqui.io/tapi'


def get_balances():
  params = {
      'method': 'getInfo',
      'nonce': int(time.time()),
  }
  params_string = urllib.parse.urlencode(params)
  signature = hmac.new(
      config.LIQUI_SECRET.encode(), params_string.encode(), hashlib.sha512
  ).hexdigest()
  headers = {
      'Key': config.LIQUI_KEY,
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


  # nonce = str(int(time.time() * 1000))
  # url = URL.format(api_key=config.TREX_KEY, nonce=nonce)
  # signature = hmac.new(
  #     config.TREX_SECRET.encode(), url.encode(), hashlib.sha512).hexdigest()
  # headers = {'apisign': signature}
  # data = requests.get(url, headers=headers).json()

  # if not data['success']:
  #   raise RuntimeError('Request failed: %s' % data['message'])

  # result = data['result']
  # balances = {item['Currency']: item['Balance'] for item in result}
  # return balances


if __name__ == '__main__':
  balances = get_balances()
  for symbol, balance in balances.items():
    if balance > 0:
      print '%6s %.3f' % (symbol, balance)
