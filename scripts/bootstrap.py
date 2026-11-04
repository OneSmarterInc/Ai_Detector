"""Development/standalone paths only; reusable packages never modify sys.path."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure():
    for path in (
        ROOT / "runtime/vendor",
        ROOT / "runtime/web-vendor",
        ROOT / "backend",
    ):
        if path.is_dir():
            sys.path.insert(0, str(path))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "standalone.settings")
    os.environ.setdefault("AI_FILE_INSPECTOR_MODEL_DIR", str(ROOT / "models/gradient"))
