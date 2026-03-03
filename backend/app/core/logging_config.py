import logging
import sys
from .config import settings

def configure_logging():
    """
    Configures the logging settings for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set lower level for some noisy libraries if needed
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
