from __future__ import print_function

import base64
import hashlib
import hmac
import time

import requests
from requests import auth

NAME = 'GDAX'
BASE_URL = 'https://api.gdax.com/'
URL = BASE_URL + 'accounts'


class CoinbaseExchangeAuth(auth.AuthBase):

  def __init__(self, api_creds):
    self.api_creds = api_creds

  def __call__(self, request):
    timestamp = str(time.time())
    message = (
        timestamp + request.method + request.path_url + (request.body or '')
    ).encode('ascii')
    hmac_key = base64.b64decode(self.api_creds['secret'])
    signature = hmac.new(hmac_key, message, hashlib.sha256)
    signature_b64 = base64.encodebytes(signature.digest()).rstrip(b'\n')

    request.headers.update({
        'CB-ACCESS-SIGN': signature_b64,
        'CB-ACCESS-TIMESTAMP': timestamp,
        'CB-ACCESS-KEY': self.api_creds['key'],
        'CB-ACCESS-PASSPHRASE': self.api_creds['passphrase'],
        'Content-Type': 'application/json',
    })
    return request


def get_balances(api_creds):
  auth = CoinbaseExchangeAuth(api_creds)
  items = requests.get(URL, auth=auth).json()
  balances = { item['currency']: float(item['balance']) for item in items }
  return balances


if __name__ == '__main__':
  balances = get_balances(api_creds)
  for symbol, balance in balances.items():
    if balance > 0:
      print('%6s %.3f' % (symbol, balance))
