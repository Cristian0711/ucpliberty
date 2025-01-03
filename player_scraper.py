import time
import queue
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, Optional, Set
from urllib.parse import urljoin
import requests


@dataclass
class Endpoints:
    BASE_URL = "https://backend.liberty.mp"
    UCP_BASE_URL = "https://ucp.liberty.mp"
    ONLINE = urljoin(BASE_URL, "/general/online")
    INVENTORY = urljoin(BASE_URL, "/general/inventory")
    PROFILE = urljoin(BASE_URL, "/user/profile/{}")
    VEHICLE_DATA = urljoin(UCP_BASE_URL, "/assets/game/vehicleData.json")
    UCP_PROFILE = urljoin(UCP_BASE_URL, "/profile/{}")


class PlayerScraper:
    def __init__(self, cache_manager, players_manager, vehicles_manager, max_workers: int = 20,
                 batch_size: int = 20, max_retries: int = 3, timeout: int = 10):
        self.cache_manager = cache_manager
        self.players_manager = players_manager
        self.vehicles_manager = vehicles_manager
        self.max_workers = max_workers
        self.batch_size = batch_size
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
            players = self.players_manager.get_players()
            for player in players:
                self.players_queue.put(player)
                self.retry_counts[player] = 0
            self.logger.info(f"Initialized scraper with {len(players)} players")
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise

    def _fetch_inventory(self) -> dict:
        response = requests.get(Endpoints.INVENTORY, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _load_token(self) -> str:
        with open('token', 'r') as f:
            return f.read().strip()

    def _process_player(self, player: str) -> bool:
        if player in self.processed:
            return True
        try:
            response = requests.get(
                Endpoints.PROFILE.format(player),
                headers={'Authorization': f'Bearer {self.bearer_token}'},
                timeout=self.timeout
            )
            if response.status_code == 200:
                self.cache_manager.update_player(player, response.text, self.vehicles)
                self.processed.add(player)
                return True
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

    def scrape_all_players(self) -> None:
        try:
            total = self.players_queue.qsize()
            self.logger.info(f"Starting scrape of {total} players")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                while not self.players_queue.empty():
                    batch = []
                    batch_size = min(self.batch_size, self.players_queue.qsize())
                    for _ in range(batch_size):
                        batch.append(self.players_queue.get())
                    futures = [executor.submit(self._process_player, player) for player in batch]
                    for future in as_completed(futures):
                        future.result()
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


def create_scraper(cache_manager, players_manager, vehicles_manager, **kwargs) -> PlayerScraper:
    scraper = PlayerScraper(cache_manager, players_manager, vehicles_manager, **kwargs)
    scraper.initialize()
    return scraper
