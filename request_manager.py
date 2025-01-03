import logging
import requests
from typing import Any


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
