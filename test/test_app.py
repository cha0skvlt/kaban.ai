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
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import app

    importlib.reload(app)
    return TestClient(app.app)


def auth_headers():
    return {"X-API-Key": "test-key"}


def test_health_no_auth(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_board_requires_api_key(client):
    response = client.get("/api/board")
    assert response.status_code == 401


def test_board_missing_configured_key(monkeypatch):
    monkeypatch.delenv("KANBAN_API_KEY", raising=False)
    import app

    importlib.reload(app)
    response = TestClient(app.app).get("/api/board", headers=auth_headers())
    assert response.status_code == 500


def test_board_get_empty_includes_starter(client):
    loaded = client.get("/api/board", headers=auth_headers())
    assert loaded.status_code == 200
    data = loaded.json()
    assert len(data["cards"]) == 1
    assert data["cards"][0]["id"] == "kaban-starter"
    assert data["cards"][0]["col"] == "ideas"


def test_board_get_and_post(client):
    board = {
        "columns": [{"id": "todo", "title": "To Do", "color": "#000"}],
        "cards": [{"id": "1", "col": "todo", "title": "Task", "labels": [], "desc": ""}],
    }
    save = client.post("/api/board", json=board, headers=auth_headers())
    assert save.status_code == 200
    assert save.json() == {"ok": True}

    loaded = client.get("/api/board", headers=auth_headers())
    assert loaded.status_code == 200
    assert loaded.json()["cards"][0]["title"] == "Task"


def test_agent_empty_command(client):
    response = client.post(
        "/api/agent",
        json={"command": "   ", "board_state": {"columns": [], "cards": []}},
        headers=auth_headers(),
    )
    assert response.status_code == 400


def test_agent_success(client):
    agent_result = {"actions": [], "message": "done"}
    with patch("app.run_agent", AsyncMock(return_value=agent_result)):
        response = client.post(
            "/api/agent",
            json={
                "command": "summarize board",
                "board_state": {"columns": [], "cards": []},
            },
            headers=auth_headers(),
        )
    assert response.status_code == 200
    assert response.json() == agent_result


def test_from_text_empty(client):
    response = client.post(
        "/api/agent/from-text",
        json={"raw_text": "   ", "board_state": {"columns": [], "cards": []}},
        headers=auth_headers(),
    )
    assert response.status_code == 400


def test_from_text_success(client):
    agent_result = {
        "actions": [{"type": "add_task", "title": "Task", "target_column": "todo", "labels": []}],
        "message": "ok",
    }
    with patch("app.run_from_text", AsyncMock(return_value=agent_result)):
        response = client.post(
            "/api/agent/from-text",
            json={
                "raw_text": "messy note",
                "board_state": {"columns": [], "cards": []},
            },
            headers=auth_headers(),
        )
    assert response.status_code == 200
    assert response.json() == agent_result


def test_from_text_llm_failure(client):
    request = httpx.Request("POST", "http://llm.test/v1/chat/completions")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("fail", request=request, response=response)

    with patch("app.run_from_text", AsyncMock(side_effect=error)):
        result = client.post(
            "/api/agent/from-text",
            json={"raw_text": "note", "board_state": {"columns": [], "cards": []}},
            headers=auth_headers(),
        )
    assert result.status_code == 502
    assert "LLM request failed" in result.json()["detail"]


def test_agent_llm_failure(client):
    request = httpx.Request("POST", "http://llm.test/v1/chat/completions")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("fail", request=request, response=response)

    with patch("app.run_agent", AsyncMock(side_effect=error)):
        result = client.post(
            "/api/agent",
            json={"command": "hello", "board_state": {"columns": [], "cards": []}},
            headers=auth_headers(),
        )
    assert result.status_code == 502
    assert "LLM request failed" in result.json()["detail"]


def test_dotenv_import_error_branch(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError("no dotenv")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("app", None)
    import app as reloaded_app

    assert reloaded_app.app.title == "KABAN AI API"
    importlib.reload(sys.modules["store"])
    importlib.reload(sys.modules["app"])
