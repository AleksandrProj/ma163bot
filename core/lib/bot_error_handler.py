from core.lib.telegram_bot import TelegramBot
from core.settings_test import NAME_BOT, CHAT_ID_TELEGRAM_BOT, TOKEN_TELEGRAM_BOT_ERROR

import time
from core.lib.bot_functions import write_log


telegram_bot = TelegramBot(TOKEN_TELEGRAM_BOT_ERROR)

# Bot work delay
def sleep_bot():
    return time.sleep(180)


# Invalid quantity error
async def quantity_err(symbol):
    print(NAME_BOT + ' - ' + symbol + 'Не хватает лотов для входа')
    await telegram_bot.send_message_error(symbol, ' - Не хватает лотов для входа')
    sleep_bot()


# Account has insufficient balance for requested action error
async def insufficient_balance_err(symbol):
    print(NAME_BOT + ' - ' + symbol + ' - Не хватает средств на балансе для входа')
    await telegram_bot.send_message_error(symbol, ' - Не хватает средств на балансе для входа')
    sleep_bot()


# Margin is insufficient error
async def margin_insufficient_err(symbol):
    print(NAME_BOT + ' - ' + symbol + ' - Не достигнут лимит по входу в сделку')
    await telegram_bot.send_message_error(symbol, ' - Не достигнут лимит по входу в сделку')
    sleep_bot()


# Order's notional must be no smaller than error
async def minimal_amount_err(symbol):
    print(NAME_BOT + ' - ' + symbol + ' - Не выполнено минимальная сумма для сделки')
    await telegram_bot.send_message_error(symbol, ' - Не выполнено минимальная сумма для сделки')
    sleep_bot()


# Default error
async def default_err(err):
    print(err)
    await write_log(err)