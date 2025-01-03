import logging

from players_manager import PlayersManager
from timer import timer
from vehicles_manager import VehiclesManager
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


def main() -> None:
    """The main function that runs the application."""
    try:
        # Initialize logging
        setup_logging()
        logging.info("Starting application...")

        # Initialize main components
        players_cache_instance = PlayerCache()
        players_manager_instance = PlayersManager()
        vehicles_manager_instance = VehiclesManager()

        with timer():
            # Create and run the scraper
            scraper = create_scraper(
                cache_manager=players_cache_instance,
                players_manager=players_manager_instance,
                vehicles_manager=vehicles_manager_instance,
                max_workers=30
            )

            # Perform scraping
            scraper.scrape_all_players()

    except Exception as e:
        logging.error(f"Application failed: {str(e)}")
        raise
    finally:
        logging.info("Application shutdown complete")


if __name__ == "__main__":
    main()
