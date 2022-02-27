from traceback import print_tb
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.enums import *
from core.lib.db_methods import Database
from core.lib.bot_functions import init_time, write_log
from core.lib.bot_error_handler import *
from core.lib.telegram_bot import TelegramBot
from core.settings_test import TAKEPROFIT, STOPLOSS, MIN_AMOUNT_ORDER, TOKEN_TELEGRAM_BOT
from decimal import Decimal
from pprint import pprint


telegram_bot = TelegramBot(TOKEN_TELEGRAM_BOT)

# Open orders
async def open_order(client: AsyncClient, db: Database, data):
    symbol = data['symbol']
    type_order = data['type_order']
    ma33 = data['moving_averange33']
    get_sl_tp = get_stoploss_takeprofit(data)
    takeprofit = get_sl_tp['takeprofit']
    stoploss = get_sl_tp['stoploss']
    lot_order = get_order_lot(data)
    current_price = data['current_price']
    limit_price = Decimal()

    if type_order == 'BUY':
        limit_price = Decimal(current_price + (current_price * Decimal('0.01'))).quantize(data['price_tick'])
    if type_order == 'SELL':
        limit_price = Decimal(current_price - (current_price * Decimal('0.01'))).quantize(data['price_tick'])

    try:
        order = await client.futures_create_order(
            symbol=symbol,
            side=type_order,
            type=FUTURE_ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=lot_order,
            price=limit_price,
            newOrderRespType=ORDER_RESP_TYPE_RESULT
        )

        pprint(order)

        # order = {
        #     'avgPrice': '7.480',
        #     'clientOrderId': 'vy9SvMvQZf4W4iEI3AQdub',
        #     'closePosition': False,
        #     'cumQty': '1',
        #     'cumQuote': '14',
        #     'executedQty': '1',
        #     'orderId': 2717765212,
        #     'origQty': '1',
        #     'origType': 'MARKET',
        #     'positionSide': 'BOTH',
        #     'price': '0',
        #     'priceProtect': False,
        #     'reduceOnly': False,
        #     'side': 'BUY',
        #     'status': 'FILLED',
        #     'stopPrice': '0',
        #     'symbol': 'ANTUSDT',
        #     'timeInForce': 'GTC',
        #     'type': 'MARKET',
        #     'updateTime': 1637098525889,
        #     'workingType': 'CONTRACT_PRICE'}   

        status = order['status']
        entry_commission = await get_commission_order(client, symbol, order['updateTime'])
        
        if status == 'FILLED' or status == 'PARTIALLY_FILLED' or status == 'NEW':
            await db.add_order(order, stoploss, takeprofit, entry_commission, ma33, True)
            await telegram_bot.send_message_open_order({
                'symbol': symbol,
                'type_order': type_order,
                'order_id': order['orderId'],
                'price': order['avgPrice'],
                'takeprofit': takeprofit,
                'stoploss': stoploss,
                'lot': order['cumQty']
            })
        elif status == 'EXPIRED':
            await db.add_order(order, stoploss, takeprofit, entry_commission, ma33, False)
        else:
            message = 'Внимание: Ордер по фьючерсу ' + symbol + ' получил статус - ' + str(status)
            print(init_time() + ' - ' + message)
            await write_log(message)

    except BinanceAPIException as err:
        message = err.message

        if 'Invalid quantity' in message:
            await quantity_err(symbol)

        if 'Account has insufficient balance for requested action' in message:
            await insufficient_balance_err(symbol)

        if 'Margin is insufficient' in message:
            await margin_insufficient_err(symbol)

        if "Order's notional must be no smaller than" in message:
            await minimal_amount_err(symbol)

        else:
            await default_err(err)

    except BinanceOrderException as err:
        message = err.message

        await default_err(message)

    except Exception as err:
        await default_err(err)

# Close orders
async def close_order(client: AsyncClient, db: Database, data):
    symbol = data['symbol']
    type_order = data['type_order']
    id_order = data['id_order']
    entry_price_order = data['entry_price']
    entry_lot_price = data['entry_lot']
    lot_order = data['lot']
    commission_entry_order = data['commission']
    side_order = SIDE_SELL if type_order == 'BUY' else SIDE_BUY
    result_order = 'Take-profit' if data['result'] else 'Stop-loss'
    current_price = data['current_price']
    limit_price = Decimal()

    if side_order == 'BUY':
        limit_price = Decimal(current_price + (current_price * Decimal('0.01'))).quantize(data['price_tick'])
    if side_order == 'SELL':
        limit_price = Decimal(current_price - (current_price * Decimal('0.01'))).quantize(data['price_tick'])

    # Алгоритм закрытия сделки
    try:
        order = await client.futures_create_order(
            symbol=symbol,
            side=side_order,
            type=FUTURE_ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=lot_order,
            price=limit_price,
            newOrderRespType=ORDER_RESP_TYPE_RESULT
        )
        pprint(order)

        exit_lot_price = order['cumQuote']
        exit_price_order = order['avgPrice']
        exit_commission = await get_commission_order(client, symbol, order['updateTime'])
        main_commission = Decimal(commission_entry_order) + Decimal(exit_commission)

        if order['status'] == 'FILLED':
            main_profit = Decimal()
            
            if type_order == 'BUY':
                main_profit = Decimal(exit_lot_price) - entry_lot_price
            elif type_order == 'SELL':
                main_profit = entry_lot_price - Decimal(exit_lot_price)

            await telegram_bot.send_message_close_order({
                'symbol': symbol,
                'type_order': type_order,
                'order_id': id_order,
                'exit_price_order': exit_price_order,
                'result_order': result_order,
                'main_profit': main_profit
            })

            await db.delete_order(id_order)
            await db.add_archived_order({
                'symbol_order': symbol,
                'id_order': id_order,
                'type_order': type_order,
                'entry_price_order': entry_price_order,
                'exit_price_order': exit_price_order,
                'entry_lot_price_order': entry_lot_price,
                'exit_lot_price_order': exit_lot_price,
                'main_commission_order': main_commission,
                'main_profit_order': main_profit,
                'lot_order': lot_order
            })
            
    except BinanceAPIException as err:
        await default_err(err)
    except Exception as err:
        await default_err(err)


# Calculation Takeprofit and Stoploss order
def get_stoploss_takeprofit(data):
    type_order = data['type_order']
    price_tick = data['price_tick']
    current_price = data['current_price']
    sl_qty_point = Decimal(current_price * Decimal(STOPLOSS)).quantize(price_tick)
    tp_qty_point = Decimal(current_price * Decimal(TAKEPROFIT)).quantize(price_tick)

    if type_order == 'BUY':
        return {
            'takeprofit': Decimal(current_price + tp_qty_point).quantize(price_tick),
            'stoploss': Decimal(current_price - sl_qty_point).quantize(price_tick)
        }

    if type_order == 'SELL':
        return {
            'takeprofit': Decimal(current_price - tp_qty_point).quantize(price_tick),
            'stoploss': Decimal(current_price + sl_qty_point).quantize(price_tick)            
        }


# Calculation qty lots for cryptocurrency
def get_order_lot(data):
    if data['price_lot'] == 1:
        return Decimal(round(Decimal(MIN_AMOUNT_ORDER / data['current_price']))).quantize(data['price_lot'])
    elif data['price_lot'] < 1:
        return Decimal(MIN_AMOUNT_ORDER / data['current_price']).quantize(data['price_lot'])


# Calculation commission
async def get_commission_order(client, symbol, update_time):
    commission = Decimal()
    commissions = await client.futures_account_trades(symbol=symbol, startTime=update_time)
    
    for data in commissions:
        commission += Decimal(data['commission'])

    return commission
