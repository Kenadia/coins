import md5
import time

import requests

from coins import config

NAME = 'CoinEx'
BASE_URL = 'https://api.coinex.com/v1/'
URL = BASE_URL + 'balance'


def get_balances():
  access_id = config.COINEX_KEY
  tonce = str(int(time.time()*1000))

  # The parameters must appear in alphabetical order, for use in the signature.
  base_param_string = 'access_id=%s&tonce=%s' % (access_id, tonce)

  url = URL + '?' + base_param_string
  param_string_to_sign = (
      base_param_string + '&secret_key=' + config.COINEX_SECRET)
  digest = md5.new(param_string_to_sign).hexdigest()
  headers = {
      'User-Agent': ('User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64) '
                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/39.0.2171.71 Safari/537.36'),
      'authorization': digest.upper(),
  }
  data = requests.get(url, headers=headers).json()['data']
  balances = {
      str(key):
      float(value['available']) + float(value['frozen'])
      for key, value in data.iteritems()
  }
  return balances


if __name__ == '__main__':
  balances = get_balances()
  for symbol, balance in balances.iteritems():
    if balance > 0:
      print '%6s %.3f' % (symbol, balance)
