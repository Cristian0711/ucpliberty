import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
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
    def __init__(self, db_file: str = "database/players_db.json"):
        self.db_file = db_file
        # Main cache for player data
        self.cache: Dict[str, PlayerData] = {}
        # Lookup cache for items and vehicles
        self.lookup_cache: Dict[str, Dict[str, int]] = {}
        self.items: Dict[str, str] = {}
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        self._load_cache()

    def _load_cache(self) -> None:
        """Load the cache from file and build the lookup cache."""
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
                    self._rebuild_lookup_cache()
                    self.logger.info(f"Loaded {len(self.cache)} players from cache")
                except Exception as e:
                    self.logger.error(f"Error loading cache: {e}")
                    self.cache = {}
                    self.lookup_cache = {}

    def _rebuild_lookup_cache(self) -> None:
        """Rebuild the lookup cache from the main cache."""
        self.lookup_cache.clear()

        for player_name, player_data in self.cache.items():
            # Add items to lookup cache with quantities
            for item_id, item in player_data.items.items():
                if item_id not in self.lookup_cache:
                    self.lookup_cache[item_id] = {}
                self.lookup_cache[item_id][player_name] = item.count

            # Add vehicles to lookup cache with quantity 1
            for vehicle in player_data.vehicles:
                vehicle_key = f"vehicle:{vehicle.name}"
                if vehicle_key not in self.lookup_cache:
                    self.lookup_cache[vehicle_key] = {}
                self.lookup_cache[vehicle_key][player_name] = 1

    def save_cache(self) -> None:
        """Save the main cache to file."""
        with self.lock:
            try:
                with open(self.db_file, 'w', encoding='utf-8') as file:
                    json.dump(
                        {name: data.to_dict() for name, data in self.cache.items()},
                        file,
                        ensure_ascii=False,
                        indent=4,
                    )

                lookup_cache_file = self.db_file.replace('.json', '_lookup.json')
                with open(lookup_cache_file, 'w', encoding='utf-8') as file:
                    lookup_data = {
                        key: list(players)
                        for key, players in self.lookup_cache.items()
                    }
                    json.dump(lookup_data, file, ensure_ascii=False, indent=4)
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

    async def update_player(self, player_name: str, inventory_data: str, vehicle_dict: Dict[int, str]) -> None:
        """Update or add a player in the cache and update lookup cache."""
        try:
            inventory_json = json.loads(inventory_data)
            user_data = inventory_json.get('user', {})

            with self.lock:
                # Remove player from existing lookup cache entries
                if player_name in self.cache:
                    old_data = self.cache[player_name]
                    for item_id in old_data.items.keys():
                        if item_id in self.lookup_cache:
                            self.lookup_cache[item_id].pop(player_name, None)
                    for vehicle in old_data.vehicles:
                        vehicle_key = f"vehicle:{vehicle.name}"
                        if vehicle_key in self.lookup_cache:
                            self.lookup_cache[vehicle_key].pop(player_name, None)

                # Update main cache
                self.cache[player_name] = PlayerData(
                    items=self._parse_inventory(user_data),
                    vehicles=self._parse_vehicles(user_data.get('personal_vehicles', []), vehicle_dict),
                    last_updated=datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                )

                # Update lookup cache with new data
                for item_id, item in self.cache[player_name].items.items():
                    if item_id not in self.lookup_cache:
                        self.lookup_cache[item_id] = {}
                    self.lookup_cache[item_id][player_name] = item.count

                for vehicle in self.cache[player_name].vehicles:
                    vehicle_key = f"vehicle:{vehicle.name}"
                    if vehicle_key not in self.lookup_cache:
                        self.lookup_cache[vehicle_key] = {}
                    self.lookup_cache[vehicle_key][player_name] = 1

            self.logger.info(f"Updated player {player_name}")
        except Exception as e:
            self.logger.error(f"Error updating player {player_name}: {e}")

    def update_items_dict(self, items: Dict[str, str]) -> None:
        self.items = items

    def get_player(self, player_name: str) -> Optional[PlayerData]:
        """Get player data from cache."""
        with self.lock:
            return self.cache.get(player_name)

    def find_users_with_item(self, item_name: str) -> Dict[str, int]:
        """Find users with a specific item and their quantities using lookup cache."""
        item_id = self.items.get(item_name)
        if not item_id:
            return {}

        with self.lock:
            return self.lookup_cache.get(item_id, {})

    def find_users_with_vehicle(self, vehicle_name: str) -> List[str]:
        """Find users with a specific vehicle using lookup cache."""
        vehicle_key = f"vehicle:{vehicle_name}"
        with self.lock:
            return list(self.lookup_cache.get(vehicle_key, set()))

    def get_player_inventory_as_string(self, player_name: str) -> Optional[PlayerData]:
        """Get player data from cache."""
        with self.lock:
            return self.cache.get(player_name)
