import coinbase.wallet.client

NAME = 'Coinbase'


def get_balances(api_creds):
  client = coinbase.wallet.client.Client(api_creds['key'], api_creds['secret'])
  accounts = client.get_accounts().data
  balances = {
      account['currency']: float(account['balance']['amount'])
      for account in accounts
  }
  return balances


if __name__ == '__main__':
  balances = get_balances(api_creds)
  for symbol, balance in balances.items():
    if balance > 0:
      print '%6s %.3f' % (symbol, balance)
