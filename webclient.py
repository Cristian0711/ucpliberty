from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dataclasses import dataclass
import logging


@dataclass
class WebClientConfig:
    chromedriver_path: str

class WebClient:
    def __init__(self, config: WebClientConfig):
        self.config = config
        self.driver = None
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        """Initializes the WebDriver with the specified configurations."""
        try:
            options = self._setup_chrome_options()
            service = Service(self.config.chromedriver_path)

            self.driver = webdriver.Chrome(
                service=service,
                options=options
            )

            self._load_cookies()
            self.logger.info("WebClient initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebClient: {str(e)}")
            raise

    def _setup_chrome_options(self) -> Options:
        """Configures Chrome options."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")
        return options

    def _load_cookies(self) -> None:
        """Loads saved cookies."""
        try:
            self.driver.get("https://ucp.liberty.mp/")

            with open('token', 'r') as file:
                token_value = file.read().strip()

            self.driver.execute_script(f"localStorage.setItem('libertymp_ucp_auth_token_v2', '{token_value}');")

            self.driver.header_overrides = {
                'Authorization': f'Bearer {token_value}'
            }
        except Exception as e:
            self.logger.error(f"Failed to load cookies: {str(e)}")

    def cleanup(self) -> None:
        """Cleans up the resources used by WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebClient cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")


def create_web_client() -> WebClient:
    """Factory function to create a WebClient instance."""
    config = WebClientConfig(
        chromedriver_path=r"C:\chromedriver\chromedriver.exe",
    )

    client = WebClient(config)
    client.initialize()
    return client
