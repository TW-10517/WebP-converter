"""Double-click launcher: .pyw starts the app with no console window."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webpconv.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
