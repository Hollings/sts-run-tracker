# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Slay the Spire 2 run tracker: a C# Harmony mod that hooks into combat events to capture per-player damage/block/card data, a FastAPI backend that merges mod output with game save files, and a React frontend dashboard.

## Build & Run Commands

### C# Mod (StS2Tracker/)
```bash
# Build (requires .NET 9 SDK)
dotnet build -p:STS2GameDir="C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2" StS2Tracker/

# Deploy to game
cp StS2Tracker/bin/StS2Tracker.dll "C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\mods\StS2Tracker\"
```
Game must be closed to deploy (DLL is locked while running).

### Backend (web/server/)
```bash
pip install fastapi uvicorn watchfiles websockets pydantic
cd web/server && python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend (web/frontend/)
```bash
cd web/frontend && npm install && npm run dev
```
Runs on port 3000. Vite proxies `/api` and `/ws` to backend on port 8000.

### Decompile game assembly (for investigating new hooks)
```bash
ilspycmd -t <FullTypeName> -r "<GameDir>\data_sts2_windows_x86_64" "<GameDir>\data_sts2_windows_x86_64\sts2.dll"
# Full project decompilation:
ilspycmd -p -o decompiled/full --nested-directories -r "<GameDir>\data_sts2_windows_x86_64" "<GameDir>\data_sts2_windows_x86_64\sts2.dll"
```

## Architecture

### Data Flow
```
Game (sts2.dll) --[Harmony hooks]--> Mod (StS2Tracker.dll) --[JSON files]--> Backend (FastAPI)
                                                                                |
Game save files (current_run.save, history/*.run, progress.save) ---------------+
                                                                                |
                                                                         merge.py combines
                                                                         both sources
                                                                                |
                                                                         Frontend (React)
                                                                         via REST + WebSocket
```

### Mod (StS2Tracker/)
- **ModEntry.cs**: Entry point. `[ModInitializer]` attribute, creates Harmony instance, calls `PatchAll`.
- **HarmonyPatches.cs**: Postfix patches on static methods in `MegaCrit.Sts2.Core.Hooks.Hook`. Every patch wraps in try/catch so tracker bugs never crash the game.
- **CombatTracker.cs**: Accumulates per-combat stats in memory, writes JSON to `%APPDATA%/SlayTheSpire2/tracker/` after each combat and on each damage-received event (for death-floor safety).

The mod manifest (`StS2Tracker.json`) sets `affects_gameplay: false`. The DLL is loaded by the game's built-in `ModManager` from `<game>/mods/StS2Tracker/`.

### Backend (web/server/)
- **main.py**: FastAPI app. `/api/live` returns merged tracker+save data, `/api/runs` lists history, `/ws` pushes live updates via WebSocket.
- **merge.py**: Core merge logic. Combines mod tracker JSON (combat detail: damage dealt, block, per-card stats) with game save files (floor-by-floor HP, gold, card/relic picks, events). Matches combats to floors by encounter name. Dynamically resolves modded vs unmodded save profile.
- **watcher.py**: Watches tracker directory for file changes, triggers WebSocket broadcasts.

### Frontend (web/frontend/)
React 19 + TypeScript + Vite + Tailwind CSS + recharts. Dark theme with amber/gold accents.
- **pages/LiveRun.tsx**: Main dashboard. Floor timeline from merged data, expandable combat detail per floor, run totals sidebar.
- **pages/RunHistory.tsx**: Table of all completed runs with filters.
- **pages/RunDetail.tsx**: Floor-by-floor historical run view.
- **pages/Stats.tsx**: Lifetime stats from progress.save (character table, card pick/win rates, encounter difficulty).
- **hooks/useWebSocket.ts**: Auto-reconnecting WebSocket hook.
- **utils/types.ts**: All TypeScript interfaces for the data model.

### Key Data Paths (Windows)
- Mod output: `%APPDATA%\SlayTheSpire2\tracker\<seed>_<timestamp>.json`
- **Primary saves (game reads/writes here):** `%APPDATA%\SlayTheSpire2\steam\<steam64id>\`
  - Modded: `.../modded/profile1/saves/`
  - Unmodded: `.../profile1/saves/`
- Cloud sync copy (NOT what the game reads): `Steam\userdata\<steam32id>\2868840\remote\`
- Multiplayer save: `current_run_mp.save` (separate from singleplayer `current_run.save`)
- Game logs: `%APPDATA%\SlayTheSpire2\logs\godot.log`
- Game install: `C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\`

## Important Conventions

- Do NOT use emojis in Python code (Windows `charmap` encoding errors).
- Game IDs (e.g. `CARD.STRIKE_IRONCLAD`) display as: split on `.`, replace `_` with space, title case -> "Strike Ironclad". Frontend has `formatGameId()`, Python has `short_id()`.
- The game uses separate save profiles for modded vs unmodded play. `merge.py` handles this with `get_save_profile_dir()` which prefers modded if it has data.
- Harmony patches target `MegaCrit.Sts2.Core.Hooks.Hook` static methods. See `HOOKS_REFERENCE.md` for all confirmed signatures.
- Player IDs are `1` in singleplayer, full Steam IDs (ulong) in multiplayer.
- The mod flushes in-progress combat data to disk on every turn start and damage received, so death floors always have partial data.

## Docs Maintenance
- If reference docs (HOOKS_REFERENCE.md, DESIGN.md, WEB_SPEC.md) are discovered to be incorrect or missing info, update them immediately. Always decompile and verify actual game API signatures before trusting the docs - they've been wrong before (e.g. AfterPowerApplied doesn't exist, actual method is AfterPowerAmountChanged).

## Reference Documentation
- `HOOKS_REFERENCE.md`: Full decompiled API surface - hook signatures, data types, identity chain, mod system details.
- `DESIGN.md`: Project roadmap, MVP/Phase 2/Phase 3 goals, risk table.
- `WEB_SPEC.md`: Web dashboard spec with data formats, component designs, Docker setup.
- `decompiled/`: ILSpy output of game types (gitignored, regenerable).
