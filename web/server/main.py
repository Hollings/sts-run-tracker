"""FastAPI backend for StS2 Tracker web dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    TrackerData,
    RunData,
    RunSummary,
    ProgressData,
)
from watcher import watch_directory, get_latest_file, read_all_runs, read_progress, _read_json
from merge import (
    merge_live_run,
    load_current_run,
    get_save_profile_dir,
    SAVE_DIR,
)

# ---------------------------------------------------------------------------
# Configuration via environment variables (with Windows defaults)
# ---------------------------------------------------------------------------

TRACKER_DIR = os.environ.get(
    "STS2_TRACKER_DIR",
    os.path.join(os.environ.get("APPDATA", ""), "SlayTheSpire2", "tracker"),
)
# Save base directory (contains both modded/profile1/saves and profile1/saves)
SAVES_BASE = os.environ.get(
    "STS2_SAVES_DIR",
    SAVE_DIR,  # from merge.py: Steam\userdata\...\remote
)
from merge import MODDED_SAVES, UNMODDED_SAVES


def _get_active_saves_dir() -> str:
    """Dynamically resolve save dir each call (modded vs unmodded)."""
    return get_save_profile_dir()


def _get_history_dir() -> str:
    return os.path.join(_get_active_saves_dir(), "history")


def _get_progress_file() -> str:
    return os.path.join(_get_active_saves_dir(), "progress.save")

HOST = os.environ.get("STS2_HOST", "0.0.0.0")
PORT = int(os.environ.get("STS2_PORT", "8000"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sts2tracker")

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WebSocket disconnected (%d total)", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Lifespan: start file watcher in background
# ---------------------------------------------------------------------------

_watcher_task: asyncio.Task | None = None


async def _on_tracker_update(data: dict[str, Any]) -> None:
    """Called by the file watcher when a tracker JSON changes."""
    logger.info("Broadcasting merged update to %d clients", len(manager._connections))
    # Merge tracker data with the current save file before broadcasting
    save = load_current_run()
    merged = merge_live_run(data, save)
    await manager.broadcast({"type": "combat_update", "data": merged})


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _watcher_task
    logger.info("Tracker dir : %s", TRACKER_DIR)
    logger.info("Saves dir   : %s", _get_active_saves_dir())
    logger.info("History dir : %s", _get_history_dir())
    logger.info("Progress    : %s", _get_progress_file())

    _watcher_task = asyncio.create_task(
        watch_directory(TRACKER_DIR, _on_tracker_update, file_pattern="*.json")
    )
    yield
    if _watcher_task:
        _watcher_task.cancel()
        try:
            await _watcher_task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="StS2 Tracker", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


def _build_merged_live() -> dict[str, Any] | None:
    """Build merged live data from tracker + save file."""
    latest = get_latest_file(TRACKER_DIR, "*.json")
    tracker = _read_json(latest) if latest else None
    save = load_current_run()
    if tracker is None and save is None:
        return None
    return merge_live_run(tracker, save)


@app.get("/api/live")
def get_live_data() -> dict[str, Any]:
    """Return merged live data from tracker + game save."""
    merged = _build_merged_live()
    if merged is None:
        return {"status": "no_data", "data": None}
    return {"status": "ok", "data": merged}


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    """Return summary of all historical runs from both modded and unmodded saves."""
    # Collect runs from both save paths, deduplicating by filename
    seen_filenames: set[str] = set()
    runs_raw: list[dict[str, Any]] = []
    for history_dir in [
        os.path.join(MODDED_SAVES, "history"),
        os.path.join(UNMODDED_SAVES, "history"),
    ]:
        for raw in read_all_runs(history_dir):
            fname = raw.get("_filename", "")
            if fname not in seen_filenames:
                seen_filenames.add(fname)
                runs_raw.append(raw)

    summaries = []
    for raw in runs_raw:
        characters = [p.get("character", "") for p in raw.get("players", [])]
        killed_by = raw.get("killed_by_encounter", "NONE.NONE")
        if killed_by == "NONE.NONE":
            killed_by = raw.get("killed_by_event", "")

        # Count floors
        floor_count = 0
        for act in raw.get("map_point_history", []):
            floor_count += len(act)

        summaries.append({
            "filename": raw.get("_filename", ""),
            "seed": raw.get("seed", ""),
            "start_time": raw.get("start_time", 0),
            "run_time": raw.get("run_time", 0),
            "win": raw.get("win", False),
            "was_abandoned": raw.get("was_abandoned", False),
            "ascension": raw.get("ascension", 0),
            "characters": characters,
            "killed_by": killed_by,
            "floor_count": floor_count,
            "game_mode": raw.get("game_mode", "standard"),
        })
    return summaries


@app.get("/api/runs/{filename}")
def get_run_detail(filename: str) -> dict[str, Any]:
    """Return full run data for a specific save file (checks both save dirs)."""
    # Search both modded and unmodded history directories
    for history_dir in [
        os.path.join(MODDED_SAVES, "history"),
        os.path.join(UNMODDED_SAVES, "history"),
    ]:
        filepath = Path(history_dir) / filename
        if filepath.exists() and filepath.is_file():
            data = _read_json(filepath)
            if data is None:
                raise HTTPException(status_code=500, detail="Failed to read run data")
            return data
    raise HTTPException(status_code=404, detail="Run not found")


@app.get("/api/progress")
def get_progress() -> dict[str, Any]:
    """Return lifetime stats from progress.save."""
    data = read_progress(_get_progress_file())
    if data is None:
        return {"status": "no_data", "data": None}
    # Return a subset of the data relevant to the dashboard
    return {
        "status": "ok",
        "data": {
            "character_stats": data.get("character_stats", []),
            "card_stats": data.get("card_stats", []),
            "encounter_stats": data.get("encounter_stats", []),
            "total_playtime": data.get("total_playtime", 0),
            "floors_climbed": data.get("floors_climbed", 0),
            "architect_damage": data.get("architect_damage", 0),
        },
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    # Send merged data immediately on connect
    merged = _build_merged_live()
    if merged:
        await ws.send_json({"type": "combat_update", "data": merged})
    try:
        while True:
            # Keep connection alive; client can send pings
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Run with uvicorn when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
