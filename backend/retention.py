"""Thin entry point for python -m backend.retention."""

import logging

from backend.interfaces.retention_cli import main


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    raise SystemExit(main())
