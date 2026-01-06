"""Main entry point for the IBKR trading bot."""
import argparse
import logging
import signal
import sys

from src.core.config import load_config, ConfigError
from src.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="IBKR Trading Bot - Automated trading with fundamentals-driven strategies",
    )

    parser.add_argument(
        "-c", "--config",
        default="config/default.yaml",
        help="Path to configuration file (default: config/default.yaml)",
    )

    parser.add_argument(
        "-l", "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    return parser.parse_args(args)


def setup_logging(level: str) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level string (DEBUG, INFO, etc.)
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parsed_args = parse_args(args)

    setup_logging(parsed_args.log_level)

    logger.info("IBKR Trading Bot starting...")
    logger.info(f"Config: {parsed_args.config}")

    orchestrator = None

    try:
        # Load configuration
        config = load_config(parsed_args.config)

        # Create and start orchestrator
        orchestrator = Orchestrator(config)

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            if orchestrator:
                orchestrator.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the orchestrator (blocks until stopped)
        orchestrator.start()

        return 0

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        if orchestrator:
            orchestrator.stop()
        return 0

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        if orchestrator:
            orchestrator.stop()
        return 1


if __name__ == "__main__":
    sys.exit(main())
