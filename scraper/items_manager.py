from scraper.request_manager import RequestManager
from scraper.request_manager import Endpoints

import json
from typing import Dict
from urllib.parse import urljoin


class ItemsManager(RequestManager):
    def __init__(self):
        super().__init__()
        self.inventory_data_endpoint = Endpoints.INVENTORY
        self.inventory_dict = {}

    def get_items(self) -> Dict[str, str]:
        try:
            response = self.make_request(self.inventory_data_endpoint)
            inventory_data = json.loads(response)
            self.inventory_dict = {
                value["name"]: key
                for key, value in inventory_data.items()
            }
            self.logger.info(f"Loaded {len(self.inventory_dict)} inventory items")
            return self.inventory_dict
        except Exception as e:
            self.logger.error(f"Failed to load inventory data: {str(e)}")
            return {}
