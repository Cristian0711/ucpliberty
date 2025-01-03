import json

from typing import Dict
from urllib.parse import urljoin

from request_manager import RequestManager


class VehiclesManager(RequestManager):
    def __init__(self, base_url: str = "https://ucp.liberty.mp"):
        super().__init__()
        self.base_url = base_url
        self.vehicle_data_endpoint = urljoin(base_url, "/assets/game/vehicleData.json")
        self.vehicle_dict = {}

    def get_vehicles(self) -> Dict[int, str]:
        try:
            response = self.make_request(self.vehicle_data_endpoint)
            vehicle_data = json.loads(response)
            self.vehicle_dict = {
                int(key): value["DisplayName"]
                for key, value in vehicle_data.items()
            }
            self.logger.info(f"Loaded {len(self.vehicle_dict)} vehicles")
            return self.vehicle_dict
        except Exception as e:
            self.logger.error(f"Failed to load vehicle data: {str(e)}")
            return {}
