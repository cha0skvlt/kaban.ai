import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import store  # noqa: E402


def _json_path() -> Path:
    env = os.environ.get("BOARD_STORE_PATH", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "backend" / "data" / "board_store.json"


def main() -> int:
    path = _json_path()
    if not path.exists():
        print(f"JSON store not found: {path}")
        return 0

    board = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(board, dict):
        raise SystemExit("Invalid JSON store: expected object at root")

    store.save_board(board)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = path.with_suffix(path.suffix + f".bak.{ts}")
    path.rename(bak)
    print(f"Imported JSON → Postgres. Renamed JSON to: {bak}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

