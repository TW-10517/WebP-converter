"""Entry point: harden the process, then start the UI."""

import logging
import logging.handlers
import os
import sys

from .security import (block_network, enable_dpi_awareness, harden_pillow,
                       set_app_id)

# Must happen before Tk is imported anywhere.
enable_dpi_awareness()
set_app_id()
harden_pillow()
block_network()


def _setup_logging():
    from . import config
    try:
        os.makedirs(config.config_dir(), exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(config.config_dir(), "app.log"),
            maxBytes=256_000, backupCount=2, encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    _setup_logging()
    from .app import App
    try:
        App().mainloop()
    except Exception:
        logging.getLogger(__name__).exception("fatal error")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
