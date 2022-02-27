import asyncio
import logging
from core.bot import Bot
from core.lib.db_methods import Database

logger = logging.getLogger(__file__)

async def start():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    bot = Bot()
    db = await Database.create()

    logger.info('Подготовка базы данных')
    await db.create_table_orders()
    await db.create_table_archived_orders()
    logger.info('База данных готова к работе')
    
    try:
        await bot.initializing(db)
        await bot.start()
        await bot.stop()
    except KeyboardInterrupt:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(start())