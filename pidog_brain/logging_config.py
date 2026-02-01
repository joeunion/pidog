"""Logging Configuration - Structured logging for PiDog brain

Provides centralized logging configuration with:
- Package-level logger
- Console output by default
- Optional file output
- Configurable log levels

Default level is INFO for clean everyday output.
Use DEBUG when troubleshooting.

Usage:
    from pidog_brain.logging_config import setup_logging, get_logger

    # Setup at application start
    setup_logging()  # INFO level by default
    setup_logging(level=logging.DEBUG)  # Verbose debugging

    # Get loggers in modules
    logger = get_logger(__name__)
    logger.info("Starting up")
    logger.error("Something failed", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Package-level logger name
PACKAGE_NAME = 'pidog_brain'

# Default format
DEFAULT_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: str = DEFAULT_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT
) -> logging.Logger:
    """Setup logging for the pidog_brain package

    Args:
        level: Logging level (default INFO)
        log_file: Optional path to log file
        format_string: Log format string
        date_format: Date format string

    Returns:
        The package-level logger
    """
    # Get package logger
    logger = logging.getLogger(PACKAGE_NAME)
    logger.setLevel(level)

    # Close and remove existing handlers to avoid leaks
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(format_string, datefmt=date_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("Message")
    """
    # Ensure the logger is a child of the package logger
    if not name.startswith(PACKAGE_NAME):
        name = f"{PACKAGE_NAME}.{name}"

    return logging.getLogger(name)


def set_level(level: int):
    """Change the logging level at runtime

    Args:
        level: New logging level (e.g., logging.DEBUG)
    """
    logger = logging.getLogger(PACKAGE_NAME)
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
