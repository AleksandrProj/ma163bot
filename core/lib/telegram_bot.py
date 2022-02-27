from aiogram import Bot
from core.settings_test import CHAT_ID_TELEGRAM_BOT, NAME_BOT


class TelegramBot:
    def __init__(self, API_TOKEN) -> None:
        self.bot = Bot(token=API_TOKEN)

    async def send_message_error(self, symbol, error):
        await self.bot.send_message(CHAT_ID_TELEGRAM_BOT, NAME_BOT + ' [' + str(symbol) + '] ' + str(error))

    async def send_message_open_order(self, data_order):
        symbol = data_order['symbol']
        type_order = data_order['type_order']
        order_id = data_order['order_id']
        price = data_order['price']
        takeprofit = data_order['takeprofit']
        stoploss = data_order['stoploss']
        lot = data_order['lot']

        await self.bot.send_message(CHAT_ID_TELEGRAM_BOT, 
                                    NAME_BOT + "\n" +
                                    symbol + ' - ' + type_order + '\n' + 
                                    'OrderID: ' + str(order_id) + '\n'
                                    'Цена сделки: ' + str(price) + '\n'
                                    'Takeprofit: ' + str(takeprofit) + '\n'
                                    'Stoploss: ' + str(stoploss) + '\n'
                                    'Lot: ' + str(lot))

    async def send_message_close_order(self, data_order):
        symbol = data_order['symbol']
        type_order = data_order['type_order']
        order_id = data_order['order_id']
        exit_price_order = data_order['exit_price_order']
        result_order = data_order['result_order']
        main_profit = data_order['main_profit']

        await self.bot.send_message(CHAT_ID_TELEGRAM_BOT,
                                    NAME_BOT + "\n" +
                                    symbol + '[ ' + type_order + ' ]' + 'СДЕЛКА ЗАКРЫТА\n' + 
                                    'OrderID: ' + str(order_id) + '\n'
                                    'Цена закрытия сделки: ' + str(exit_price_order) + '\n'
                                    'Результат: закрыта по ' + result_order + '\n'
                                    'Прибыль: ' + str(main_profit) + '$')