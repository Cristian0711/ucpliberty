import asyncio
import aiohttp
import queue
import logging
import requests

from typing import Dict, Set
from misc.timer import timer

from scraper.request_manager import Endpoints


class PlayerScraper:
    def __init__(self, cache_manager, players_manager, vehicles_manager, items_manager, max_retries: int = 3,
                 timeout: int = 10):
        self.cache_manager = cache_manager
        self.players_manager = players_manager
        self.vehicles_manager = vehicles_manager
        self.items_manager = items_manager

        self.max_retries = max_retries
        self.timeout = timeout
        self.players_queue = queue.Queue()
        self.retry_counts: Dict[str, int] = {}
        self.processed: Set[str] = set()
        self.inventory = None
        self.vehicles = None
        self.bearer_token = None
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        try:
            self.inventory = self._fetch_inventory()
            self.vehicles = self.vehicles_manager.get_vehicles()
            self.bearer_token = self._load_token()
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise

    def load_players(self) -> None:
        players = self.players_manager.get_players()
        for player in players:
            self.players_queue.put(player)
            self.retry_counts[player] = 0

    def _fetch_inventory(self) -> dict:
        response = requests.get(Endpoints.INVENTORY, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _load_token(self) -> str:
        with open('database/token', 'r') as f:
            return f.read().strip()

    async def _process_player(self, player: str) -> bool:
        if player in self.processed:
            return True
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        Endpoints.PROFILE.format(player),
                        headers={'Authorization': f'Bearer {self.bearer_token}'},
                        timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        await self.cache_manager.update_player(player, data, self.vehicles)
                        self.processed.add(player)
                        return True
                    else:
                        self._handle_retry(player)
                        return False
        except Exception as e:
            self.logger.error(f"Failed to process {player}: {e}")
            self._handle_retry(player)
            return False

    def _handle_retry(self, player: str) -> None:
        if self.retry_counts[player] < self.max_retries:
            self.retry_counts[player] += 1
            self.players_queue.put(player)

    async def scrape_all_players(self) -> None:
        try:
            items = self.items_manager.get_items()
            self.cache_manager.update_items_dict(items)

            self.processed.clear()
            self.load_players()

            total = self.players_queue.qsize()
            self.logger.info(f"Starting scrape of {total} players")

            tasks = []
            while not self.players_queue.empty():
                player = self.players_queue.get()
                tasks.append(self._process_player(player))

            with timer():
                await asyncio.gather(*tasks)

            self._log_results(total)
            self.cache_manager.save_cache()
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            raise

    def _log_results(self, total: int) -> None:
        failed = [p for p, count in self.retry_counts.items() if count >= self.max_retries]
        success_rate = (len(self.processed) / total) * 100
        self.logger.info(f"Scraping completed: {len(self.processed)}/{total} players processed ({success_rate:.1f}%)")
        if failed:
            self.logger.warning(f"Failed players: {', '.join(failed)}")


def create_scraper(cache_manager, players_manager, vehicles_manager, items_manager, **kwargs) -> PlayerScraper:
    scraper = PlayerScraper(cache_manager, players_manager, vehicles_manager, items_manager, **kwargs)
    scraper.initialize()
    return scraper
