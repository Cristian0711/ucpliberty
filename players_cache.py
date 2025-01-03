import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging
from threading import Lock


@dataclass
class PlayerVehicle:
    model_hash: int
    name: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlayerItem:
    name: str
    count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlayerData:
    items: Dict[str, 'PlayerItem']
    vehicles: List['PlayerVehicle']
    last_updated: str

    def __init__(self, items, vehicles, last_updated: str):
        self.items = items
        self.vehicles = vehicles
        self.last_updated = last_updated

    def to_dict(self) -> dict:
        return {
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "vehicles": [vehicle.to_dict() for vehicle in self.vehicles],
            "last_updated": self.last_updated,
        }


class PlayerCache:
    def __init__(self, db_file: str = "players_db.json"):
        self.db_file = db_file
        self.cache: Dict[str, PlayerData] = {}
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        self._load_cache()

    def _load_cache(self) -> None:
        """Load the cache from file."""
        with self.lock:
            if os.path.exists(self.db_file):
                try:
                    with open(self.db_file, 'r', encoding='utf-8') as file:
                        raw_data = json.load(file)
                        self.cache = {
                            name: PlayerData(
                                items={k: PlayerItem(**v) for k, v in data['items'].items()},
                                vehicles=[PlayerVehicle(**v) for v in data['vehicles']],
                                last_updated=data['last_updated'],
                            )
                            for name, data in raw_data.items()
                        }
                    self.logger.info(f"Loaded {len(self.cache)} players from cache")
                except Exception as e:
                    self.logger.error(f"Error loading cache: {e}")
                    self.cache = {}

    def save_cache(self) -> None:
        """Save the cache to file."""
        with self.lock:
            try:
                with open(self.db_file, 'w', encoding='utf-8') as file:
                    json.dump(
                        {name: data.to_dict() for name, data in self.cache.items()},
                        file,
                        ensure_ascii=False,
                        indent=4,
                    )
                self.logger.info("Cache saved successfully")
            except Exception as e:
                self.logger.error(f"Error saving cache: {e}")

    def _parse_inventory(self, user_data_json: dict) -> Dict[str, PlayerItem]:
        """Parse player's inventory."""

        def add_items(source_items: List[dict], items: Dict[str, PlayerItem]):
            for item in source_items:
                item_key = item.get('item_key')
                if not item_key:
                    continue
                if item_key in items:
                    items[item_key].count += 1
                else:
                    items[item_key] = PlayerItem(name=item_key, count=1)

        final_items = {}
        add_items(user_data_json.get('Inventory', {}).get('Items', []), final_items)
        add_items(user_data_json.get('PostOfficeItems', []), final_items)

        return final_items

    def _parse_vehicles(self, vehicles_json: List[dict], vehicle_dict: Dict[int, str]) -> List[PlayerVehicle]:
        """Parse player's vehicles."""
        return [
            PlayerVehicle(
                model_hash=vehicle.get('ModelHash'),
                name=vehicle_dict.get(vehicle.get('ModelHash'), "Unknown Vehicle"),
            )
            for vehicle in vehicles_json
        ]

    def update_player(self, player_name: str, inventory_data: str, vehicle_dict: Dict[int, str]) -> None:
        """Update or add a player in the cache."""
        try:
            inventory_json = json.loads(inventory_data)
            user_data = inventory_json.get('user', {})

            with self.lock:
                self.cache[player_name] = PlayerData(
                    items=self._parse_inventory(user_data),
                    vehicles=self._parse_vehicles(user_data.get('personal_vehicles', []), vehicle_dict),
                    last_updated=datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                )

            self.logger.info(f"Updated player {player_name}")
        except Exception as e:
            self.logger.error(f"Error updating player {player_name}: {e}")

    def get_player(self, player_name: str) -> Optional[PlayerData]:
        """Get player data from cache."""
        with self.lock:
            return self.cache.get(player_name)
