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

import os
from pathlib import Path
from typing import Any, Optional

import httpx
from agent import run_agent, run_from_text
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from store import get_board, save_board

# Load .env when running outside Docker (optional)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

app = FastAPI(title="KABAN AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BoardState(BaseModel):
    columns: list[Any] = Field(default_factory=list)
    cards: list[Any] = Field(default_factory=list)
    labels: list[Any] = Field(default_factory=list)


class AgentRequest(BaseModel):
    command: str
    board_state: BoardState


class FromTextRequest(BaseModel):
    raw_text: str
    board_state: BoardState


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    expected = os.environ.get("KANBAN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="KANBAN_API_KEY is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/board", dependencies=[Depends(verify_api_key)])
def read_board():
    return get_board()


@app.post("/api/board", dependencies=[Depends(verify_api_key)])
def write_board(board: BoardState):
    save_board(board.model_dump())
    return {"ok": True}


@app.post("/api/agent", dependencies=[Depends(verify_api_key)])
async def agent(req: AgentRequest):
    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="command is required")
    try:
        return await run_agent(command, req.board_state.model_dump())
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc


@app.post("/api/agent/from-text", dependencies=[Depends(verify_api_key)])
async def agent_from_text(req: FromTextRequest):
    raw_text = req.raw_text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="raw_text is required")
    try:
        return await run_from_text(raw_text, req.board_state.model_dump())
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc
