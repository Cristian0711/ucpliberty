from contextlib import contextmanager
import time
from typing import Generator
import logging


@contextmanager
def timer() -> Generator[None, None, None]:
    """Context manager for measuring execution time."""
    start_time = time.time()
    yield
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Task completed in {elapsed_time:.2f} seconds")