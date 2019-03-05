import base64
import hashlib
import hmac
import time

import requests
from requests import auth

from coins import config

NAME = 'GDAX'
BASE_URL = 'https://api.gdax.com/'
URL = BASE_URL + 'accounts'


class CoinbaseExchangeAuth(auth.AuthBase):

  def __init__(self, api_key, secret_key, passphrase):
    self.api_key = api_key
    self.secret_key = secret_key
    self.passphrase = passphrase

  def __call__(self, request):
    timestamp = str(time.time())
    message = (
        timestamp + request.method + request.path_url + (request.body or ''))
    hmac_key = base64.b64decode(self.secret_key)
    signature = hmac.new(hmac_key, message, hashlib.sha256)
    signature_b64 = signature.digest().encode('base64').rstrip('\n')

    request.headers.update({
        'CB-ACCESS-SIGN': signature_b64,
        'CB-ACCESS-TIMESTAMP': timestamp,
        'CB-ACCESS-KEY': self.api_key,
        'CB-ACCESS-PASSPHRASE': self.passphrase,
        'Content-Type': 'application/json',
    })
    return request


def get_balances():
  auth = CoinbaseExchangeAuth(
      config.GDAX_KEY, config.GDAX_SECRET, config.GDAX_PASSPHRASE)
  items = requests.get(URL, auth=auth).json()
  balances = {item['currency']: float(item['balance']) for item in items}
  return balances


if __name__ == '__main__':
  balances = get_balances()
  for symbol, balance in balances.iteritems():
    if balance > 0:
      print '%6s %.3f' % (symbol, balance)
