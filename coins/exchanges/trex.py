from __future__ import print_function

import hashlib
import hmac
import time

import requests

NAME = 'Bittrex'
BASE_URL = 'https://bittrex.com/api/v1.1/'
URL = BASE_URL + 'account/getbalances?apikey={api_key}&nonce={nonce}'


def get_balances(api_creds):
  nonce = str(int(time.time() * 1000))
  url = URL.format(api_key=api_creds['key'], nonce=nonce)
  signature = hmac.new(
      api_creds['secret'].encode(), url.encode(), hashlib.sha512
  ).hexdigest()
  headers = { 'apisign': signature }
  data = requests.get(url, headers=headers).json()

  if not data['success']:
    raise RuntimeError('{} request failed: {}'.format(NAME, data['message']))

  result = data['result']
  balances = { item['Currency']: item['Balance'] for item in result }
  return balances


if __name__ == '__main__':
  balances = get_balances(api_creds)
  for symbol, balance in balances.items():
    if balance > 0:
      print('%6s %.3f' % (symbol, balance))
