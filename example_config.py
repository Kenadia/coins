# Config used by main.py.
EXCHANGES = [
    # 'cb',
    # 'coinex',
    # 'gdax',
    # 'hitbtc',
    # 'liqui',
    # 'polo',
    # 'trex',
]
CACHE_FILE = 'balances.pickle'

# Config used by coins.Exchanges.
SYMBOL_TRANSFORM = {
    'STR': 'XLM',
}
REQUIRED_ROWS = []

# Credentials used by coins.CMC.
COINMARKETCAP_KEY = '...'

# Exchange API credentials, used by coins.Exchanges.
EXCHANGE_KEYS = {
    'cb': {
        'key': '...',
        'secret': '...',
    },
    'coinex': {
        'access_id': '...',
        'secret': '...',
    },
    'gdax': {
        'key': '...',
        'passphrase': '...',
        'secret': '...',
    },
    'hitbtc': {
        'key': '...',
        'secret': '...',
    },
    'liqui': {
        'key': '...',
        'secret': '...',
    },
    'polo': {
        'key': '...',
        'secret': '...',
    },
    'trex': {
        'key': '...',
        'secret': '...',
    },
}
