# StS2 Run Tracker

A Slay the Spire 2 mod + web dashboard that captures detailed per-player combat stats (damage dealt, block, cards played, kills) and displays them in a live browser dashboard alongside game save data.

## Components

- **C# Harmony mod** hooks into combat events, writes JSON to disk
- **FastAPI backend** merges mod output with game save files, serves REST + WebSocket
- **React frontend** live dashboard with run history, per-floor detail, and lifetime stats

## Install the mod

1. Build or download `StS2Tracker.dll` and copy it with the manifest into the game's mods directory:
   ```
   <game>/mods/StS2Tracker/
       StS2Tracker.json
       StS2Tracker.dll
   ```

2. Launch Slay the Spire 2. First launch with a new mod shows a confirmation popup -- accept it, the game quits, then relaunch.

3. On the second launch the mod loads automatically. `[StS2Tracker]` messages in the game log confirm it's running.

## Run the web dashboard

### Backend

```bash
pip install fastapi uvicorn watchfiles websockets pydantic
cd web/server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Do **not** use `--reload` -- it spawns zombie child processes on Windows.

### Frontend

```bash
cd web/frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser. The navbar shows the dashboard URL so you can share it with co-op partners on your network.

## Save files

Modded runs use a separate save profile from unmodded runs. To sync progress between them:

```
%APPDATA%/SlayTheSpire2/steam/<STEAM_ID>/
├── profile1/          <- unmodded saves
│   ├── saves/         (current_run, progress, prefs, history/)
│   └── replays/
└── modded/
    └── profile1/      <- modded saves
        ├── saves/
        └── replays/
```

**Copy unmodded to modded** (bring vanilla progress into modded):
```bash
STEAM="$APPDATA/SlayTheSpire2/steam/<YOUR_STEAM_ID>"
cp "$STEAM/profile1/saves/"*.save "$STEAM/modded/profile1/saves/"
cp "$STEAM/profile1/saves/"*.save.backup "$STEAM/modded/profile1/saves/"
cp "$STEAM/profile1/saves/history/"* "$STEAM/modded/profile1/saves/history/"
cp "$STEAM/profile1/replays/"* "$STEAM/modded/profile1/replays/"
```

**Copy modded to unmodded** (bring modded progress back to vanilla):
```bash
cp "$STEAM/modded/profile1/saves/"*.save "$STEAM/profile1/saves/"
cp "$STEAM/modded/profile1/saves/"*.save.backup "$STEAM/profile1/saves/"
cp "$STEAM/modded/profile1/saves/history/"* "$STEAM/profile1/saves/history/"
cp "$STEAM/modded/profile1/replays/"* "$STEAM/modded/profile1/replays/"
```

Close the game before copying save files.

There's also a script that automates this: `python scripts/sync_saves.py`

## What the mod tracks

Data the base game does **not** save, captured via Harmony hooks:

| Stat | Per-player | Per-turn | Per-target |
|------|-----------|----------|------------|
| Damage dealt | Yes | Yes | Yes |
| Damage taken | Yes | - | - |
| Damage blocked | Yes | - | - |
| Block gained | Yes | Yes | - |
| Cards played | Yes | Yes | - |
| Card play sequence | Yes | Yes | Yes |
| Kills | Yes | - | - |

Pet/minion damage is attributed to the owning player.

## Output

Tracker JSON is written to:
```
%APPDATA%\SlayTheSpire2\tracker\<seed>_<timestamp>.json
```

The backend auto-discovers save files from `%APPDATA%\SlayTheSpire2\steam\` and merges them with tracker data.

## Building the mod from source

Requires .NET 9 SDK.

```bash
dotnet build -p:STS2GameDir="<path to Slay the Spire 2>" StS2Tracker/
```

Copy `StS2Tracker/bin/StS2Tracker.dll` to `<game>/mods/StS2Tracker/`.

## CLI tools

Legacy terminal-based tools (work without the web dashboard):

```bash
python sts2_tracker.py summary       # overall stats
python sts2_tracker.py runs          # list all runs
python sts2_tracker.py run -r -1     # latest run detail
python live_tracker.py               # real-time terminal dashboard
```

## Project structure

```
slaythespiredata/
    StS2Tracker/              # C# Harmony mod
        src/
            ModEntry.cs       # mod entry point
            CombatTracker.cs  # data collection + JSON export
            HarmonyPatches.cs # Harmony hooks into game events
    web/
        server/               # FastAPI backend
            main.py           # REST + WebSocket endpoints
            merge.py          # tracker + save file merge logic
            watcher.py        # file watcher for live updates
        frontend/             # React + TypeScript + Tailwind
            src/
                pages/        # LiveRun, RunHistory, RunDetail, Stats
                components/   # Navbar, floor panels, charts
                hooks/        # WebSocket auto-reconnect
    scripts/
        sync_saves.py         # copy saves between modded/unmodded profiles
    DESIGN.md                 # project roadmap
    HOOKS_REFERENCE.md        # decompiled game API reference
```
