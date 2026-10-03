import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """Configures structured application logging without exposing secrets."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Suppress verbose noise from third-party libraries in info mode
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if not debug else logging.DEBUG)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger("studyspace.api")
