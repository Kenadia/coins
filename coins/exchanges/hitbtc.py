import collections
import requests

from coins import config

NAME = 'HitBTC'
BASE_URL = 'https://api.hitbtc.com/api/2/'
URL_1 = BASE_URL + 'account/balance'
URL_2 = BASE_URL + 'trading/balance'


def get_balances():
  session = requests.session()
  session.auth = (config.HITBTC_KEY, config.HITBTC_SECRET)
  balances = collections.defaultdict(float)

  for url in [URL_1, URL_2]:
    data = session.get(url).json()
    for item in data:
      amount = float(item['available']) + float(item['reserved'])
      balances[item['currency']] += amount

  return balances


if __name__ == '__main__':
  balances = get_balances()
  for symbol, balance in balances.iteritems():
    if balance > 0:
      print '%6s %.3f' % (symbol, balance)
