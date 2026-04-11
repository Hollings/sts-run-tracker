"""File watcher for tracker JSON and save files.

Uses watchfiles to monitor directories and notify connected WebSocket clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Coroutine

from watchfiles import awatch, Change

logger = logging.getLogger("sts2tracker.watcher")


async def watch_directory(
    directory: str | Path,
    callback: Callable[[dict[str, Any]], Coroutine],
    file_pattern: str = "*.json",
) -> None:
    """Watch a directory for file changes and invoke a callback.

    The callback is always invoked for matching files, even if the file
    could not be parsed as JSON (save files are often mid-write when
    ``awatch`` fires). On parse failure the callback receives ``{}`` —
    callers that need fresh state should re-read from disk themselves.

    Args:
        directory: Path to watch.
        callback: Async function called with parsed JSON (or ``{}``) when a
                  file matching *file_pattern* is created or modified.
        file_pattern: Glob pattern for files to watch (default ``*.json``).
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning("Watch directory does not exist yet: %s", dir_path)
        # Wait for the directory to appear
        while not dir_path.exists():
            await asyncio.sleep(2)
        logger.info("Watch directory now exists: %s", dir_path)

    logger.info("Watching %s for %s changes", dir_path, file_pattern)

    async for changes in awatch(str(dir_path)):
        for change_type, changed_path in changes:
            changed = Path(changed_path)
            # Only care about created/modified files matching the pattern
            if change_type in (Change.added, Change.modified):
                if changed.match(file_pattern) and changed.is_file():
                    try:
                        # Best-effort JSON parse — save files may be
                        # mid-write and unparseable. Callbacks that don't
                        # need the payload still fire with an empty dict
                        # so they can re-read from disk themselves.
                        parsed = _read_json(changed)
                        if parsed is not None:
                            logger.info(
                                "File %s: %s",
                                "created" if change_type == Change.added else "modified",
                                changed.name,
                            )
                        else:
                            logger.debug(
                                "File %s (unparseable, firing anyway): %s",
                                "created" if change_type == Change.added else "modified",
                                changed.name,
                            )
                        await callback(parsed or {})
                    except Exception:
                        logger.exception("Error processing %s", changed)


def _read_json(path: Path) -> dict[str, Any] | None:
    """Read and parse a JSON file, returning None on failure."""
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read JSON from %s: %s", path, exc)
        return None


def get_latest_file(directory: str | Path, pattern: str = "*.json") -> Path | None:
    """Return the most recently modified file matching *pattern* in *directory*."""
    dir_path = Path(directory)
    if not dir_path.exists():
        return None
    files = sorted(dir_path.glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def read_all_runs(directory: str | Path) -> list[dict[str, Any]]:
    """Read all .run files from the history directory."""
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    runs = []
    for run_file in sorted(dir_path.glob("*.run"), key=os.path.getmtime, reverse=True):
        data = _read_json(run_file)
        if data is not None:
            data["_filename"] = run_file.name
            runs.append(data)
    return runs


def read_progress(filepath: str | Path) -> dict[str, Any] | None:
    """Read the progress.save file."""
    return _read_json(Path(filepath))
