import logging

from players_manager import PlayersManager
from timer import timer
from vehicles_manager import VehiclesManager
from webclient import create_web_client
from players_cache import PlayerCache
from player_scraper import create_scraper


def setup_logging() -> None:
    """Configures the logging system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scraper.log', mode='a', encoding='utf-8')
        ]
    )
    # Suppress INFO logs for seleniumwire
    seleniumwire_logger = logging.getLogger('seleniumwire')
    seleniumwire_logger.setLevel(logging.WARNING)


def main() -> None:
    """The main function that runs the application."""
    try:
        # Initialize logging
        setup_logging()
        logging.info("Starting application...")

        # Initialize main components
        webclient_instance = create_web_client()
        players_cache_instance = PlayerCache()
        players_manager_instance = PlayersManager()
        vehicles_manager_instance = VehiclesManager()

        with timer():
            # Create and run the scraper
            scraper = create_scraper(
                webclient=webclient_instance,
                players_cache=players_cache_instance,
                players_manager=players_manager_instance,
                vehicles_manager=vehicles_manager_instance,
                batch_size=20
            )

            # Perform scraping
            scraper.scrape_all_players()

    except Exception as e:
        logging.error(f"Application failed: {str(e)}")
        raise
    finally:
        # Cleanup
        if 'webclient_instance' in locals():
            webclient_instance.cleanup()
        logging.info("Application shutdown complete")


if __name__ == "__main__":
    main()
