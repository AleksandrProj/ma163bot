import asyncpg
from asyncpg import Pool, Connection
from datetime import datetime
from core.settings_test import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

class Database:
    def __init__(self, pool) -> None:
        self.pool: Pool = pool

    @classmethod
    async def create(cls):
        pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME            
        )

        return cls(pool)

    async def execute(self, command, *args,
                      fetch: bool = False,
                      fetchval: bool = False,
                      fetchrow: bool = False,
                      execute: bool = False):
        async with self.pool.acquire() as connection:
            connection: Connection
            async with connection.transaction():
                if fetch:
                    result = await connection.fetch(command, *args)
                elif fetchval:
                    result = await connection.fetchval(command, *args)
                elif fetchrow:
                    result = await connection.fetchrow(command, *args)
                elif execute:
                    result = await connection.execute(command, *args)
            return result

    async def create_table_orders(self):
        sql = """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            date TIMESTAMP NOT NULL,
            symbol VARCHAR(100) NOT NULL,
            order_id BIGINT NOT NULL UNIQUE,
            client_order_id VARCHAR(255) NOT NULL UNIQUE,
            price DECIMAL NOT NULL,
            stoploss DECIMAL NOT NULL,
            takeprofit DECIMAL NOT NULL,
            moving_averange33 DECIMAL NOT NULL,
            status_order VARCHAR(100) NOT NULL,
            type_order VARCHAR(4) NOT NULL,
            lot DECIMAL NOT NULL,
            price_lot DECIMAL NOT NULL,
            commission DECIMAL NOT NULL,
            active_order BOOLEAN DEFAULT false
        )
        """
        await self.execute(sql, execute=True)

    async def create_table_archived_orders(self):
        sql = """
        CREATE TABLE IF NOT EXISTS archived_orders (
            id SERIAL PRIMARY KEY,
            date TIMESTAMP NOT NULL,
            symbol VARCHAR(100) NOT NULL,
            order_id BIGINT NOT NULL UNIQUE,
            entry_price DECIMAL NOT NULL,
            exit_price DECIMAL NOT NULL,
            entry_lot_price DECIMAL NOT NULL,
            exit_lot_price DECIMAL NOT NULL,
            type_order VARCHAR(4) NOT NULL,
            lot DECIMAL NOT NULL,
            commission_order DECIMAL NOT NULL,
            profit DECIMAL NOT NULL
        )
        """
        await self.execute(sql, execute=True)
    
    async def add_order(self, data_order, stoploss, takeprofit, commission, moving_averange33, active_order):
        sql = """
        INSERT INTO orders (
            date,
            symbol,
            order_id,
            client_order_id,
            price,
            stoploss,
            takeprofit,
            moving_averange33,
            status_order,
            type_order,
            lot,
            price_lot,
            commission,
            active_order
        )
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        """
        await self.execute(
            sql,
            datetime.now(),
            data_order['symbol'],
            data_order['orderId'],
            data_order['clientOrderId'],
            data_order['avgPrice'],
            stoploss,
            takeprofit,
            moving_averange33,
            data_order['status'],
            data_order['side'],
            data_order['cumQty'],
            data_order['cumQuote'],
            commission,
            active_order,
            execute=True
        )

    async def add_archived_order(self, data_order):
        sql = """
        INSERT INTO archived_orders (
            date,
            symbol,
            order_id,
            entry_price,
            exit_price,
            entry_lot_price,
            exit_lot_price,
            type_order,
            lot,
            commission_order,
            profit
        )
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """
        await self.execute(
            sql,
            datetime.now(),
            data_order['symbol_order'],
            data_order['id_order'],
            data_order['entry_price_order'],
            data_order['exit_price_order'],
            data_order['entry_lot_price_order'],
            data_order['exit_lot_price_order'],
            data_order['type_order'],
            data_order['lot_order'],
            data_order['main_commission_order'],
            data_order['main_profit_order'],
            execute=True
        )

    async def update_status_info_order(self, data):
        sql = f"""
        UPDATE orders
        SET price='{data["price"]}', status_order='{data["status"]}', lot='{data["lot"]}', price_lot='{data["price_lot"]}', commission='{data["commission"]}'
        WHERE order_id='{data["orderID"]}'
        """
        await self.execute(sql, execute=True)

    async def update_tp_sl_order(self, data):
        sql = f"""
        UPDATE orders
        SET stoploss='{data["stoploss"]}', takeprofit='{data["takeprofit"]}', moving_averange33='{data["moving_averange33"]}'
        WHERE order_id='{data["order_id"]}'
        """
        await self.execute(sql, execute=True)
    
    async def check_open_order(self, symbol):
        sql = f"""
        SELECT *
        FROM orders
        WHERE symbol='{symbol}' AND active_order=true
        """
        return await self.execute(sql, fetchrow=True)

    async def get_used_balance(self):
        sql = f"""
        SELECT SUM(price_lot) used_balance 
        FROM orders
        """
        return await self.execute(sql, fetchrow=True)

    async def delete_order(self, id):
        sql = f"""
        DELETE FROM orders
        WHERE order_id={id}
        """
        await self.execute(sql, execute=True)