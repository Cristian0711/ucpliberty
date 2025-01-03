import time
import brotli
import queue
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from request_manager import RequestManager
from players_manager import PlayersManager
from vehicles_manager import VehiclesManager
from timer import timer


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
    def __init__(self, webclient, players_cache, players_manager: PlayersManager,
                 vehicles_manager: VehiclesManager, batch_size: int = 20, queue_size: int = 2000):
        self.webclient = webclient
        self.players_cache = players_cache
        self.players_manager = players_manager
        self.vehicles_manager = vehicles_manager
        self.batch_size = batch_size
        self.inventory_list = None
        self.players_queue = queue.Queue(maxsize=queue_size)
        self.retry_queue = queue.Queue()
        self.players_list = []
        self.vehicle_dict = {}
        self.max_retries = 3
        self.player_attempts = {}

        self.logger = logging.getLogger(__name__)

        self.request_manager = RequestManager()

    def _get_user_profile_response(self, player_name: str) -> Optional[bytes]:
        """Checks for a response related to a user's profile request."""
        target_url = f'/user/profile/{player_name}'
        for request in self.webclient.driver.requests:
            if request.response and target_url in request.url:
                return request.response.body
        return None

    def _add_to_retry_queue(self, player_name: str) -> None:
        """Adds a player to the retry queue."""
        attempts = self.player_attempts.get(player_name, 0) + 1
        self.player_attempts[player_name] = attempts

        if attempts < self.max_retries:
            self.logger.warning(f"Adding {player_name} to retry queue (attempt {attempts}/{self.max_retries})")
            self.retry_queue.put(player_name)
        else:
            self.logger.error(f"Failed to process {player_name} after {self.max_retries} attempts")

    def _process_player(self, handle: str, player_name: str, response_body: bytes):
        try:
            player_inventory = brotli.decompress(response_body).decode('utf-8')
            self.players_cache.update_player(player_name, player_inventory, self.vehicle_dict)

            try:
                self.webclient.driver.switch_to.window(handle)
                self.webclient.driver.close()
            except Exception as e:
                self.logger.error(f"Error closing window for {player_name}: {str(e)}")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error processing player {player_name}: {str(e)}")
            return False

    def _process_batch(self) -> None:
        """Processes a batch of players."""
        active_users: List[Tuple[str, str]] = []
        processed_count = 0

        # Choose the queue for processing
        queue_to_use = self.retry_queue if not self.retry_queue.empty() else self.players_queue
        current_batch_size = min(self.batch_size, queue_to_use.qsize())

        self.logger.info(
            f"Processing batch of {current_batch_size} players from {'retry' if queue_to_use == self.retry_queue else 'main'} queue")

        # Open pages for the batch
        for _ in range(current_batch_size):
            if queue_to_use.empty():
                break

            player_name = queue_to_use.get()
            try:
                self.webclient.driver.execute_script(
                    f"window.open('{Endpoints.PROFILE.format(player_name)}');"
                )
                handles = self.webclient.driver.window_handles
                active_users.append((handles[-1], player_name))
            except Exception as e:
                self.logger.error(f"Failed to open page for {player_name}: {str(e)}")
                self._add_to_retry_queue(player_name)

        # Process responses
        start_time = time.time()
        while active_users and (time.time() - start_time < 15):  # Global timeout for batch
            for user in active_users[:]:
                body = self._get_user_profile_response(user[1])
                if body is None:
                    time.sleep(0.1)
                    continue

                if self._process_player(user[0], user[1], body):
                    processed_count += 1

                active_users.remove(user)

        # Cleanup for unprocessed users
        for handle, player_name in active_users:
            try:
                self.webclient.driver.switch_to.window(handle)
                self.webclient.driver.close()
                self._add_to_retry_queue(player_name)
            except Exception as e:
                self.logger.error(f"Error during cleanup for {player_name}: {str(e)}")

        # Switch back to the main tab
        try:
            handles = self.webclient.driver.window_handles
            self.webclient.driver.switch_to.window(handles[0])

            # Clear requests
            del self.webclient.driver.requests
        except Exception as e:
            self.logger.error(f"Error during batch cleanup: {str(e)}")

        self.logger.info(
            f"Batch completed: {processed_count}/{current_batch_size} players processed, "
            f"Main queue: {self.players_queue.qsize()}, "
            f"Retry queue: {self.retry_queue.qsize()}"
        )

    def scrape_all_players(self) -> None:
        """Main function for scraping all players."""
        try:
            total_players = self.players_queue.qsize()
            self.logger.info(f"Starting scraping for {total_players} players")

            while not (self.players_queue.empty() and self.retry_queue.empty()):
                with timer():
                    self._process_batch()

            # Final statistics
            failed_players = [name for name, attempts in self.player_attempts.items()
                              if attempts >= self.max_retries]

            self.logger.info(f"Scraping completed. Failed players: {len(failed_players)}")
            if failed_players:
                self.logger.warning(f"Failed players: {', '.join(failed_players)}")

            self.players_cache.save_cache()
        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}")
            raise

    def initialize_data(self) -> None:
        try:
            self.logger.info("Starting data initialization...")
            self.inventory_list = self.request_manager.make_request(Endpoints.INVENTORY)
            self.players_list = self.players_manager.get_players()
            self.vehicle_dict = self.vehicles_manager.get_vehicles()

            for player in self.players_list:
                self.players_queue.put(player)

            self.logger.info(f"Initialized with {len(self.players_list)} players")
        except Exception as e:
            self.logger.error(f"Data initialization failed: {str(e)}")
            raise


def create_scraper(webclient, players_cache, players_manager: PlayersManager,
                   vehicles_manager: VehiclesManager, batch_size: int = 20) -> PlayerScraper:
    scraper = PlayerScraper(webclient, players_cache, players_manager, vehicles_manager, batch_size)
    scraper.initialize_data()
    return scraper
