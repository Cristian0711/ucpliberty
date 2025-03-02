import discord
from discord.ext import commands
import logging
from typing import Optional

from scraper.items_manager import ItemsManager
from misc.logging_config import setup_logging

from scraper.players_manager import PlayersManager
from scraper.vehicles_manager import VehiclesManager
from scraper.players_cache import PlayerCache
from scraper.player_scraper import create_scraper, PlayerScraper


class ScrapingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

        # Initialize components as None
        self.players_cache: Optional[PlayerCache] = None
        self.players_manager: Optional[PlayersManager] = None
        self.vehicles_manager: Optional[VehiclesManager] = None
        self.items_manager: Optional[ItemsManager] = None
        self.scraper: Optional[PlayerScraper] = None

        # Setup logging
        setup_logging()
        self.logger = logging.getLogger(__name__)

    async def setup_hook(self):
        """Initialize all necessary components when the bot starts."""
        try:
            # Initialize managers
            self.players_cache = PlayerCache()
            self.players_manager = PlayersManager()
            self.vehicles_manager = VehiclesManager()
            self.items_manager = ItemsManager()

            # Create scraper with dependencies
            self.scraper = create_scraper(
                cache_manager=self.players_cache,
                players_manager=self.players_manager,
                vehicles_manager=self.vehicles_manager,
                items_manager=self.items_manager
            )

            self.players_cache.update_items_dict(self.items_manager.get_items())

            # Sync commands
            await self.tree.sync()

            self.logger.info("Bot setup completed successfully")
        except Exception as e:
            self.logger.error(f"Failed to setup bot: {e}")
            raise

    async def on_ready(self):
        """Event handler for when the bot is ready."""
        self.logger.info(f"{self.user.name} is online and ready!")