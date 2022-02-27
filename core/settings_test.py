import os
from environs import Env

env = Env()
env.read_env()

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {
    'logs': os.path.join(BASEDIR, 'logs', 'bot_logs.txt'),
    'orders': os.path.join(BASEDIR, 'files', 'orders.csv'),
    'archive_orders': os.path.join(BASEDIR, 'files', 'archive_orders.csv')
}

# Settings telegram bot
TOKEN_TELEGRAM_BOT = env.str('API_TOKEN_TB')
TOKEN_TELEGRAM_BOT_ERROR = env.str('API_TOKEN_TB_ERR')
CHAT_ID_TELEGRAM_BOT = env.str('CHAT_ID_TB')

# APIs data
API_KEY = env.str('API_KEY')
API_SECRET = env.str('API_SECRET')

# Data database
DB_HOST = env.str('DB_HOST')
DB_PORT = env.str('DB_PORT')
DB_USER = env.str('DB_USER')
DB_PASS = env.str('DB_PASS')
DB_NAME = env.str('DB_NAME')

# Settings bot
NAME_BOT = 'MA163 Bot [Futures]'
BIG_TIMEFRAME = '5m'
SMALL_TIMEFRAME = '1m'
TIMEOUT_BOT = 0.01

# Data bot
BUDGET = 50                 # Equivalent to dollar
MAX_PRICE_FUTURES = 10      # Maximum price futeres
MIN_AMOUNT_ORDER = 10       # Minimal size order
MIN_BALANCE_BNB = 0.01       # Minimal balance BNB
AMOUNT_ORDER_BNB = 0.03     # Amount topup BNB
BIG_MA = 163                # Period big moving averange 
SMALL_MA = 33               # Period small moving averange
STOPLOSS = 0.01             # Size stoploss level (0.5% - 1%)
TAKEPROFIT = 0.03           # Size takeprofit level (Stoploss * multiplier)