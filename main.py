import asyncio

from bot.scraping_bot import ScrapingBot
from bot.commands import setup_commands


async def main():
    try:
        client = ScrapingBot()
        setup_commands(client)
        await client.start('MTMyNDgyMjAyNzczMDk0NDA2MQ.GrGrTP.okXp03BqxvFvJy9AQKWJCnI-CB4ikE5psPQ9MY')
    except Exception as e:
        client.logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
