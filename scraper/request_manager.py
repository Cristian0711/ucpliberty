import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from typing import Any

@dataclass
class Endpoints:
    BASE_URL = "https://backend.liberty.mp"
    UCP_BASE_URL = "https://ucp.liberty.mp"
    ONLINE = urljoin(BASE_URL, "/general/online")
    INVENTORY = urljoin(BASE_URL, "/general/inventory")
    PROFILE = urljoin(BASE_URL, "/user/profile/{}")
    VEHICLE_DATA = urljoin(UCP_BASE_URL, "/assets/game/vehicleData.json")
    UCP_PROFILE = urljoin(UCP_BASE_URL, "/profile/{}")

class RequestManager:
    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def make_request(self, url: str, timeout: int = 10) -> Any:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Request failed for {url}: {str(e)}")
            raise
