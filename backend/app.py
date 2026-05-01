from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REAL_BACKEND_DIR = Path(__file__).resolve().parents[1] / "code" / "backend"
REAL_APP_PATH = REAL_BACKEND_DIR / "app.py"

if str(REAL_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(REAL_BACKEND_DIR))

spec = importlib.util.spec_from_file_location("fraudlens_backend_app", REAL_APP_PATH)

if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load backend app from {REAL_APP_PATH}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

app = module.app


if __name__ == "__main__":
    module.app.run(host="0.0.0.0", port=int(module.os.getenv("PORT", "5000")))
