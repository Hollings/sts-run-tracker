# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Slay the Spire 2 run tracker: a C# Harmony mod that hooks into combat events to capture per-player damage/block/card data, embeds an HTTP server serving a React dashboard directly from the game at `http://localhost:52323`.

## Build & Run Commands

### C# Mod (StS2Tracker/)
```bash
# Build (requires .NET 9 SDK)
dotnet build -p:STS2GameDir="C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2" StS2Tracker/

# Deploy to game
cp StS2Tracker/bin/StS2Tracker.dll "C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\mods\StS2Tracker\"
```
Game must be closed to deploy (DLL is locked while running).

### Frontend (web/frontend/)
```bash
cd web/frontend && npm install && npm run build
```
Produces `web/frontend/dist/` with `index.html` and `assets/`. Deploy by copying to the game mods directory:
```bash
cp -r web/frontend/dist/* "C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\mods\StS2Tracker\web\"
```
The mod's embedded HTTP server serves these files at `http://localhost:52323`.

For frontend development with hot reload:
```bash
cd web/frontend && npm run dev
```
Runs on port 3000. Vite proxies `/api` and `/ws` to port 8000 (requires the Python dev server below).

### Dev server (web/server/) -- development only
```bash
pip install fastapi uvicorn watchfiles websockets pydantic
cd web/server && python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Do NOT use `--reload` flag - it spawns child processes that become zombies on Windows. This server is only needed for frontend development with hot reload. In production, the mod serves everything.

Port collision override: the default is 8000 to match `docker-compose.yml`. If something else is already on 8000, set `STS2_PORT=<port>` when launching the server and `STS2_BACKEND_PORT=<port>` when launching Vite so the proxy matches.

### Dev server file-based fallback
The dev server normally gets its combat data from JSON files written by the C# mod's `CombatTracker` to `%APPDATA%/SlayTheSpire2/tracker/`. When the mod is disabled (or hasn't loaded yet, or was never enabled in the first place), it falls back to reading directly from the game's own `current_run.save` / `current_run_mp.save` files. You lose per-combat detail (damage charts, card play sequences) since those are mod-tracked, but the dashboard still shows the map, floor history, card/relic choices, and per-floor HP/gold from whatever the game has autosaved.

Key pieces in `web/server/`:
- `main.py` — `_build_merged_live()` is the single entry point both watchers go through. There are two `watch_directory` tasks running in `lifespan`: one on the tracker dir, one on `get_save_profile_dir()` matching `current_run*.save`. Both fire `_rebuild_and_broadcast()`, which re-reads from disk.
- `merge.py` — `load_active_run()` (no history fallback) for the live view; `load_current_or_latest_run()` keeps the old history-fallback behavior for any REST callers. `merge_live_run()` discards the stale tracker (not the save) when their seeds mismatch.
- `watcher.py` — `watch_directory` now fires the callback even on JSON parse failure (save files are often mid-write when `awatch` reports a change); callers re-read from disk themselves.

Stale-file detection: STS2 doesn't clean up `current_run*.save` or the tracker's JSON output when a run ends, so files from weeks-old runs can linger on disk. `merge.current_session_start_time()` returns the mtime of the newest archived `godot*.log` file (STS2 rotates `godot.log` on every session start), and any save/tracker file older than that is rejected as orphaned. This is what stops the dashboard from showing a dead run as if it were live.

### Decompile game assembly (for investigating new hooks)
```bash
ilspycmd -t <FullTypeName> -r "<GameDir>\data_sts2_windows_x86_64" "<GameDir>\data_sts2_windows_x86_64\sts2.dll"
# Full project decompilation:
ilspycmd -p -o decompiled/full --nested-directories -r "<GameDir>\data_sts2_windows_x86_64" "<GameDir>\data_sts2_windows_x86_64\sts2.dll"
```

## Architecture

### Data Flow
```
Game (sts2.dll) --[Harmony hooks]--> Mod (StS2Tracker.dll)
                                        |
                                        +-- Tracks combat stats in memory (CombatTracker)
                                        +-- Reads game save files (SaveFileReader)
                                        +-- Merges both sources (MergeEngine)
                                        +-- Embedded HTTP server (HttpServer, port 52323)
                                        |   +-- REST API: /api/live, /api/runs, /api/progress
                                        |   +-- WebSocket: /ws (live combat updates)
                                        |   +-- Static files: built React frontend
                                        |
                                     Browser (http://localhost:52323)
```

### Mod (StS2Tracker/src/)
- **ModEntry.cs**: Entry point. `[ModInitializer]` attribute, creates Harmony instance, starts HTTP server.
- **HarmonyPatches.cs**: Postfix patches on `MegaCrit.Sts2.Core.Hooks.Hook` static methods. Every patch wraps in try/catch so tracker bugs never crash the game. Includes pause menu patch that adds "STS Tracker" button.
- **CombatTracker.cs**: Accumulates per-combat stats in memory with `ReaderWriterLockSlim` for thread safety. Writes JSON to `%APPDATA%/SlayTheSpire2/tracker/` as backup. Fires `OnDataChanged` callback for WebSocket broadcasts.
- **HttpServer.cs**: `System.Net.HttpListener` on a background thread. Routes REST API, WebSocket, and static file requests. `RunOnMainThread()` pattern for safe game state access.
- **SaveFileReader.cs**: Reads game save files from disk. Auto-discovers save directory from `%APPDATA%`. Handles modded vs unmodded profiles.
- **MergeEngine.cs**: Merges in-memory combat data with save file floor history. Builds unified run view with per-floor detail, combat stats, and run totals.
- **ApiHandlers.cs**: REST endpoint handlers for /api/live, /api/runs, /api/progress.
- **WebSocketManager.cs**: Manages WebSocket connections, broadcasts combat updates to all clients.
- **StatusOverlay.cs**: Godot CanvasLayer showing dashboard URL in top-right corner.

### Frontend (web/frontend/)
React 19 + TypeScript + Vite + Tailwind CSS + recharts. StS2 theme: `#183749` dark blue bg, `#F2F0C4` light yellow text, `#8B1913` dark red accents.
- **pages/LiveRun.tsx**: Main dashboard. Left 2/3 shows selected floor detail, right 1/3 has run totals + clickable floor list. Auto-shows victory summary on boss win.
- **pages/RunHistory.tsx**: Table of all completed runs with filters.
- **pages/RunDetail.tsx**: Floor-by-floor historical run view with per-player HP chart.
- **pages/Stats.tsx**: Lifetime stats from progress.save.
- **hooks/useWebSocket.ts**: Auto-reconnecting WebSocket hook.
- **utils/types.ts**: All TypeScript interfaces for the data model.

### Key Data Paths (Windows)
- Mod output: `%APPDATA%\SlayTheSpire2\tracker\<seed>_<timestamp>.json`
- **Primary saves (game reads/writes here):** `%APPDATA%\SlayTheSpire2\steam\<steam64id>\`
  - Modded: `.../modded/profile1/saves/`
  - Unmodded: `.../profile1/saves/`
- Game logs: `%APPDATA%\SlayTheSpire2\logs\godot.log`
- Game install: `C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\`

## Important Conventions

- Do NOT use emojis in Python code (Windows `charmap` encoding errors).
- Game IDs (e.g. `CARD.STRIKE_IRONCLAD`) display as: split on `.`, replace `_` with space, title case -> "Strike Ironclad". Frontend has `formatGameId()`, C# has `MergeEngine.ShortId()`.
- The game uses separate save profiles for modded vs unmodded play. `SaveFileReader` handles this with `GetSaveProfileDir()` which prefers modded if it has data.
- Harmony patches target `MegaCrit.Sts2.Core.Hooks.Hook` static methods. See `HOOKS_REFERENCE.md` for all confirmed signatures.
- Player IDs are `1` in singleplayer, full Steam IDs (ulong) in multiplayer.
- The mod flushes in-progress combat data on every turn start and damage received, so death floors always have partial data.
- CombatTracker uses `ReaderWriterLockSlim` -- HTTP threads read via `GetSnapshot()`/`GetSnapshotJson()`, game thread writes under write lock.

## Docs Maintenance
- If reference docs (HOOKS_REFERENCE.md, DESIGN.md, WEB_SPEC.md) are discovered to be incorrect or missing info, update them immediately. Always decompile and verify actual game API signatures before trusting the docs.

## Reference Documentation
- `HOOKS_REFERENCE.md`: Full decompiled API surface - hook signatures, data types, identity chain, mod system details.
- `DESIGN.md`: Project roadmap, MVP/Phase 2/Phase 3 goals, risk table.
- `WEB_SPEC.md`: Web dashboard spec with data formats, component designs.
- `decompiled/`: ILSpy output of game types (gitignored, regenerable).
