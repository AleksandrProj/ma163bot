from datetime import datetime
from decimal import Decimal
from core.settings_test import BIG_TIMEFRAME, FILES, BIG_MA, SMALL_MA, SMALL_TIMEFRAME, TOKEN_TELEGRAM_BOT_ERROR, \
                               MIN_BALANCE_BNB, AMOUNT_ORDER_BNB
from core.lib.telegram_bot import TelegramBot

from binance.client import Client, AsyncClient
from binance.exceptions import BinanceAPIException


# Connection telegram bot
telegram_bot = TelegramBot(TOKEN_TELEGRAM_BOT_ERROR)

# Time initilization
def init_time():
    return datetime.now().ctime()

async def write_log(error, symbol=None):
        await telegram_bot.send_message_error(symbol, error)
        with open(FILES['logs'], 'at') as fout:
                fout.write(init_time() + ' - ' + str(error) + '\n')

# Расчет скользящих средних
async def get_calculation_ma(self, symbol):
        avg_price_big = Decimal()
        avg_price_small = Decimal()
        high_price_last_bar = Decimal()
        low_price_last_bar = Decimal()
        last_close_prices_2_bars = []
        qty_last_bars_big = '815 minutes ago UTC' if BIG_TIMEFRAME == Client.KLINE_INTERVAL_5MINUTE else ''
        qty_last_bars_small = '33 minutes ago UTC' if SMALL_TIMEFRAME == Client.KLINE_INTERVAL_1MINUTE else ''     

        try:
                info_last_candlestick_big = await self.client.futures_historical_klines(symbol, BIG_TIMEFRAME, qty_last_bars_big)
                info_last_candlestick_small = await self.client.futures_historical_klines(symbol, SMALL_TIMEFRAME, qty_last_bars_small)
        except BinanceAPIException as err:
                err = "Ошибка в функции get_calculation_ma: " + str(err)
                await write_log(self, err)
        except Exception as err:
            err = "Ошибка в функции get_calculation_ma: " + str(err)
            await write_log(self, err)

        for index, last_bar in enumerate(info_last_candlestick_big):
                avg_price_big += Decimal(last_bar[4])

        for index, last_bar in enumerate(info_last_candlestick_small):
                avg_price_small += Decimal(last_bar[4])
                
                if len(info_last_candlestick_small) - 1 > index >= len(info_last_candlestick_small) - 3:
                        last_close_prices_2_bars.append(Decimal(last_bar[4]))
                        high_price_last_bar = Decimal(last_bar[2])
                        low_price_last_bar = Decimal(last_bar[3])

        return {
                'avg_price_big_ma': Decimal(avg_price_big / BIG_MA),
                'avg_price_small_ma': Decimal(avg_price_small / SMALL_MA),
                'last_close_prices_two_bars': last_close_prices_2_bars,
                'last_high_price_bar': high_price_last_bar,
                'last_low_price_bar': low_price_last_bar
        }

# get balance account
async def get_balance(client: AsyncClient, topup_symbol):
        account_balance_info = await client.futures_account_balance()
        price_size = '0.00000001' if topup_symbol == 'BNB' else '0.01'
        return Decimal([asset for asset in account_balance_info if asset['asset'] == topup_symbol][0]['balance']).quantize(Decimal(price_size))

# Topup balance BNB
async def topup_bnb(client: AsyncClient):
        """ Top up BNB balance if it drops below minimum specified balance """
        bnb_balance = await get_balance(client, 'BNB')

        if bnb_balance < MIN_BALANCE_BNB:
                qty = round(Decimal(AMOUNT_ORDER_BNB) - bnb_balance, 5)
                order = await client.order_market_buy(symbol='BNBUSDT', quantity=qty)
                return order
        return False