from pprint import pprint
from threading import Thread
import time
import math
from decimal import Decimal
from traceback import print_tb

from binance import ThreadedWebsocketManager
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException
from core.lib.bot_functions import get_calculation_ma, init_time, write_log, topup_bnb, get_balance
from core.lib.db_methods import Database
from core.lib.order_methods import open_order, close_order, get_stoploss_takeprofit, get_commission_order
from core.settings_test import API_KEY, API_SECRET, TIMEOUT_BOT, MAX_PRICE_FUTURES, BUDGET, MIN_AMOUNT_ORDER


class Bot:
    def __init__(self) -> None:
        self.db = None
        self.client = None
        self.twm = None
        self.current_pricies = {}
        self.info_futures = {}
        self.price_tick_size = {}
        self.price_lot_size = {}
        self.list_streams = []
        self.is_require_ma33 = {}

    # COMPUTED BOT FUNCTION
    # Update data orders (stoploss, takeprofit) in DB
    async def update_ma33(self, data):
        symbol = data['symbol']
        id_order = data['order_id']
        type_order = data['type_order']
        ma33_order = data['ma33']
        price_tick = self.price_tick_size[symbol]
        current_price = self.current_pricies[symbol]

        # Получение новых Takeprofit and Stoploss
        get_sl_tp = get_stoploss_takeprofit({
            'type_order': type_order,
            'price_tick': price_tick,
            'current_price': current_price
        })

        # Обновление данных в БД
        await self.db.update_tp_sl_order({
            'order_id': id_order,
            'takeprofit': get_sl_tp['takeprofit'],
            'stoploss': get_sl_tp['stoploss'],
            'moving_averange33': ma33_order
        })

    # Get information futures
    async def get_info_futures(self, symbol):
        try:
            for info_contract in self.info_futures:
                if info_contract['symbol'] == symbol:
                    for info_contract_filter in info_contract['filters']:
                        filter_type = info_contract_filter['filterType']
                        if filter_type == 'PRICE_FILTER':
                            self.price_tick_size[symbol] = Decimal(
                                info_contract_filter['tickSize'])
                        elif filter_type == 'LOT_SIZE':
                            self.price_lot_size[symbol] = Decimal(
                                info_contract_filter['stepSize']).normalize()
        except BinanceAPIException as err:
            await write_log(err.message, symbol=symbol)

    # MAIN BOT FUNCTIONS
    def connection_socket(self, symbol):
        self.list_streams.extend([
            self.twm.start_aggtrade_futures_socket(
                callback=self.handle_socket, symbol=symbol),
            # self.twm.start_user_socket(callback=self.handle_socket)
        ])

        self.current_pricies[symbol] = 0

    def handle_socket(self, data):
        try:
            if data['data']:
                self.current_pricies[data['data']['s']
                                     ] = Decimal(data['data']['p'])
        except KeyError as err:
            err = "Ошибка в функции handle_socket: " + str(err)
            print(err)
            # write_log(err)
        except Exception as err:
            err = "Ошибка в функции handle_socket: " + str(err)
            print(err)
            # write_log(err)

    async def initializing(self, db: Database):
        # Инициализация базы данных
        self.db = db

        # Подключение к асинхронному клиенту
        self.client = await AsyncClient.create(API_KEY, API_SECRET)

        # Подключение к сокету
        self.twm = ThreadedWebsocketManager(API_KEY, API_SECRET)
        self.twm.start()

        # Получение информации по фьючерсам
        self.info_futures = await self.client.futures_exchange_info()
        self.info_futures = self.info_futures['symbols']

    # TRADE FUNCTION
    async def find_entry_point(self, data):
        symbol = data['symbol']
        price = data['price']
        price_tick = data['price_tick']
        price_lot = data['price_lot']

        # Calculation MA163 and MA33
        data_ma = await get_calculation_ma(self, symbol)
        ma163 = data_ma['avg_price_big_ma']
        ma33 = data_ma['avg_price_small_ma']
        close_price_last_bars = data_ma['last_close_prices_two_bars']
        high_price_last_bar = data_ma['last_high_price_bar']
        low_price_last_bar = data_ma['last_low_price_bar']

        # Вычисление касалась ли предыдыщая свеча MA33
        is_touch_ma33 = high_price_last_bar >= ma33 >= low_price_last_bar

        print(init_time() + ' Ищем точку входа для ' + symbol)

        # await open_order(self.client, self.db, {
        #     'symbol': symbol,
        #     'type_order': 'SELL',
        #     'price_tick': price_tick[symbol],
        #     'price_lot': price_lot[symbol],
        #     'current_price': price,
        #     'moving_averange33': ma33
        # })

        # time.sleep(5)

        # BUY
        # if price > ma163:
        #     if is_touch_ma33:
        #         if close_price_last_bars[1] > ma33:
        #             print('Совершаем сделку в покупку')
        #             await open_order(self.client, self.db, {
        #                 'symbol': symbol,
        #                 'type_order': 'BUY',
        #                 'price_tick': price_tick[symbol],
        #                 'price_lot': price_lot[symbol],
        #                 'current_price': price,
        #                 'moving_averange33': ma33
        #             })

        # SELL
        # if price < ma163:
        #     if is_touch_ma33:
        #         if close_price_last_bars[1] < ma33:
        #             print('Совершаем сделку в продажу')
        #             await open_order(self.client, self.db, {
        #                 'symbol': symbol,
        #                 'type_order': 'SELL',
        #                 'price_tick': price_tick[symbol],
        #                 'price_lot': price_lot[symbol],
        #                 'current_price': price,
        #                 'moving_averange33': ma33
        #             })

    # Start trading
    async def start_trade(self, data):
        if 0 < data['price'] < MAX_PRICE_FUTURES:
            await self.find_entry_point(data)

    async def monitoring_trade(self, data):
        symbol = data['symbol']
        price = data['price']
        price_tick = data['price_tick']
        data_open_order = data['order_data']

        # Data open order
        id_order = data_open_order['order_id']
        type_order = data_open_order['type_order']
        tp_order = data_open_order['takeprofit']
        sl_order = data_open_order['stoploss']
        status_order = data_open_order['status_order']
        entry_price = Decimal(data_open_order['price'])
        entry_lot = Decimal(data_open_order['price_lot'])
        lot_order = Decimal(data_open_order['lot'])
        commission_order = Decimal(data_open_order['commission'])
        ma33_order = Decimal(data_open_order['moving_averange33'])

        print(init_time() + ' Мониторинг по открытой сделке - ' + symbol)

        # if 0 < price:
        #     await close_order(self.client, self.db, {
        #         'symbol': symbol,
        #         'type_order': type_order,
        #         'id_order': id_order,
        #         'entry_price': entry_price,
        #         'entry_lot': entry_lot,
        #         'lot': lot_order,
        #         'commission': commission_order,
        #         'current_price': price,
        #         'price_tick': price_tick[symbol],
        #         'result': True
        #     })

        #     print('Сделка закрыта')
        #     time.sleep(5)

        # Если ОРДЕР был исполнен частично
        if status_order == 'PARTIALLY_FILLED' or status_order == 'NEW':
            order_query = await self.client.futures_get_order(symbol=symbol, orderId=id_order)

            if order_query['status'] == 'FILLED':
                await self.db.update_status_info_order({
                    'orderID': order_query['orderId'],
                    'status': order_query['status'],
                    'price': order_query['avgPrice'],
                    'lot': order_query['executedQty'],
                    'price_lot': order_query['cumQuote'],
                    'commission': await get_commission_order(self.client, symbol, order_query['updateTime'])
                })

        # Если ОРДЕР был исполнен полностью
        if status_order == 'FILLED':
            # Calculation MA163 and MA33
            data_ma = await get_calculation_ma(self, symbol)
            ma33 = data_ma['avg_price_small_ma']
            high_price_last_bar = data_ma['last_high_price_bar']
            low_price_last_bar = data_ma['last_low_price_bar']

            # Вычисление касалась ли предыдыщая свеча MA33
            is_touch_ma33 = high_price_last_bar >= ma33 >= low_price_last_bar

            if type_order == 'BUY':
                # Выход по stoploss
                if 0 < price <= sl_order:
                    # Здесь установить функцию для выхода из позиции
                    print('Позиция закрыта по Stoploss - BUY')

                    await close_order(self.client, self.db, {
                        'symbol': symbol,
                        'type_order': type_order,
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order,
                        'current_price': price,
                        'price_tick': price_tick[symbol],
                        'result': False
                    })

                # Выход по takeprofit
                if 0 < price >= tp_order:
                    # Здесь установить функцию для выхода из позиции
                    print('Позиция закрыта по Takeprofit - BUY')

                    await close_order(self.client, self.db, {
                        'symbol': symbol,
                        'type_order': type_order,
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order,
                        'current_price': price,
                        'price_tick': price_tick[symbol],
                        'result': True
                    })

                # Перенос позиции за новый экстремум при новом касания MA33
                if is_touch_ma33:
                    if ma33 > ma33_order:
                        print('Перенос ордеров BUY')
                        await self.update_ma33({
                            'symbol': symbol,
                            'order_id': id_order,
                            'type_order': type_order,
                            'ma33': ma33
                        })

            if type_order == 'SELL':
                # Выход по stoploss
                if 0 < price >= sl_order:
                    # Здесь установить функцию для выхода из позиции
                    print('Позиция закрыта по Stoploss - SELL')

                    await close_order(self.client, self.db, {
                        'symbol': symbol,
                        'type_order': type_order,
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order,
                        'current_price': price,
                        'price_tick': price_tick[symbol],
                        'result': False
                    })

                # Выход по takeprofit
                if 0 < price <= tp_order:
                    # Здесь установить функцию для выхода из позиции
                    print('Позиция закрыта по Takeprofit - SELL')

                    await close_order(self.client, self.db, {
                        'symbol': symbol,
                        'type_order': type_order,
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order,
                        'current_price': price,
                        'price_tick': price_tick[symbol],
                        'result': True
                    })

                # Перенос позиции за новый экстремум при новом касания MA33
                if is_touch_ma33:
                    if ma33 < ma33_order:
                        print('Перенос ордеров SELL')
                        await self.update_ma33({
                            'symbol': symbol,
                            'order_id': id_order,
                            'type_order': type_order,
                            'ma33': ma33
                        })

    async def start(self):
        list_symbols = []

        while True:
            list_trade_symbols = []
            list_open_orders = []
            minimal_quantity_deals = 0

            print(init_time() + ' - Бот ожидает сделок')

            for info_contract in self.info_futures:
                price_sym = await self.client.get_aggregate_trades(symbol=info_contract['symbol'])
                price_sym = Decimal(price_sym[-1]['p'])

                if price_sym < 50:                    
                    trade_symbol = info_contract['symbol']
                    is_open_order = await self.db.check_open_order(trade_symbol)
                    query_used_balance = await self.db.get_used_balance()
                    used_balance = 0 if query_used_balance['used_balance'] is None else query_used_balance['used_balance']
                    minimal_qty_deals = math.floor(
                        (Decimal(BUDGET) - used_balance) / MIN_AMOUNT_ORDER)
                    name_stream = str(trade_symbol).lower() + '@aggTrade'

                    # Добавление незарегистрированных потоков
                    if name_stream not in self.list_streams:
                        if info_contract['contractType'] != 'CURRENT_QUARTER' \
                            or info_contract['contractType'] != '':
                                # Добавление потока фьючерса в массив
                                list_symbols.append(trade_symbol)

                                # # Получение информации по фьючерсу (Конфликт потока и асинхронности)
                                get_info_futures = Thread(target=self.get_info_futures, args=(trade_symbol,))
                                get_info_futures.start()
                                get_info_futures.join()

                                # # Подписка на сокет фьючерса
                                start_socket_symbol = Thread(target=self.connection_socket, args=(trade_symbol,))
                                start_socket_symbol.start()
                                start_socket_symbol.join()

            time.sleep(1)

        # Рабочий код для одной валюты
        # symbol = 'SOLUSDT'

        # self.connection_socket(symbol)

        # while True:
        #     is_open_order = await self.db.check_open_order(symbol)
        #     query_used_balance = await self.db.get_used_balance()
        #     used_balance = 0 if query_used_balance['used_balance'] is None else query_used_balance['used_balance']
        #     minimal_qty_deals = math.floor((Decimal(BUDGET) - used_balance) / MIN_AMOUNT_ORDER)

        #     print(init_time() + ' - Бот ожидает сделок')

        #     # topup_order_bnb = await topup_bnb(self.client)
        #     await self.get_info_futures(symbol)

        #     if is_open_order is None:
        #         # Можно торговать
        #         if minimal_qty_deals > 0:
        #             await self.start_trade({
        #                 'symbol': symbol,
        #                 'price': self.current_pricies[symbol],
        #                 'price_lot': self.price_lot_size,
        #                 'price_tick': self.price_tick_size,
        #             })

        #         # Торговать нельзя, можно только мониторить открытые сделки
        #         if minimal_qty_deals < 1:
        #             # Monitoring position order
        #             await self.monitoring_trade({
        #                 'symbol': symbol,
        #                 'price': self.current_pricies[symbol],
        #                 'price_tick': self.price_tick_size,
        #                 'order_data': is_open_order
        #             })
        #     else:
        #         # Monitoring position order
        #         await self.monitoring_trade({
        #             'symbol': symbol,
        #             'price': self.current_pricies[symbol],
        #             'price_tick': self.price_tick_size,
        #             'order_data': is_open_order
        #         })

        #     # 4 Сделать функцию подписки на сокеты всех доступных символов биржи

        #     time.sleep(1 * 60 * TIMEOUT_BOT)

    async def stop(self):
        print('Stopped bot')
        await self.client.close_connection()
        self.twm.stop()
