import json

from datetime import datetime
from typing import List
from urllib.parse import urljoin

from request_manager import RequestManager


class PlayersManager(RequestManager):
    def __init__(self, base_url: str = "https://backend.liberty.mp"):
        super().__init__()
        self.base_url = base_url
        self.online_endpoint = urljoin(base_url, "/general/online")

    def get_players(self) -> List[str]:
        try:
            db_file = "online_db.json"
            online_json = self.make_request(self.online_endpoint)
            parsed_data = json.loads(online_json)
            players = parsed_data.get('users', [])

            try:
                with open(db_file, "r") as f:
                    current_db = json.load(f)
            except FileNotFoundError:
                current_db = []

            updated_db = self._update_database(players, current_db)

            with open(db_file, "w") as f:
                json.dump(updated_db, f, indent=4)

            self.logger.info(f"Number of online players: {len(players)}")
            return [user['name'] for user in updated_db]
        except Exception as e:
            self.logger.error(f"Failed to load online players: {str(e)}")
            return []

    def _update_database(self, new_players: List[dict], current_db: List[dict]) -> List[dict]:
        current_db_dict = {user['name']: user for user in current_db}
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for player in new_players:
            name = player['name']
            if name in current_db_dict:
                current_db_dict[name]['last_online'] = current_time
            else:
                current_db_dict[name] = {
                    'name': name,
                    'last_online': current_time
                }
        return list(current_db_dict.values())
