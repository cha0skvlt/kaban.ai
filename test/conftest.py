# KABAN AI
# Copyright (C) 2026 Eugene Tomashkov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _reload_backend_modules():
    for name in ("store", "agent", "app"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])


@pytest.fixture(autouse=True)
def env_and_store(tmp_path, monkeypatch):
    store_file = tmp_path / "board_store.json"
    monkeypatch.setenv("BOARD_STORE_PATH", str(store_file))
    monkeypatch.setenv("KANBAN_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-llm-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    # Keep tests isolated from repo .env
    try:
        import dotenv

        monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    except ImportError:
        pass

    _reload_backend_modules()
    yield store_file
