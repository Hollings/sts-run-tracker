# StS2 Run Tracker

A Slay the Spire 2 mod that captures detailed per-player combat stats and displays them in a live browser dashboard. The dashboard is built into the mod -- no separate server or setup required.

## Install

1. [Download the latest release](https://github.com/Hollings/sts-run-tracker/releases) and place the files in your game's mods directory:
   ```
   <game>/mods/StS2Tracker/
       StS2Tracker.dll
       StS2Tracker.json
       web/
           index.html
           assets/
   ```

2. Launch Slay the Spire 2. Accept the mod confirmation popup, relaunch.

3. Open `http://localhost:52323` in your browser.

The pause menu also has an "STS Tracker" button that opens the dashboard directly.

## Save files

Modded runs use a **separate save profile** from unmodded runs. Your vanilla progress won't carry over automatically.

```
%APPDATA%/SlayTheSpire2/steam/<STEAM_ID>/
+-- profile1/          <- unmodded saves
|   +-- saves/         (current_run, progress, prefs, history/)
|   +-- replays/
+-- modded/
    +-- profile1/      <- modded saves
        +-- saves/
        +-- replays/
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

Close the game before copying. There's also a script: `python scripts/sync_saves.py`

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

## Building from source

Requires .NET 9 SDK and Node.js.

```bash
# Build the mod
dotnet build -p:STS2GameDir="<path to Slay the Spire 2>" StS2Tracker/

# Build the frontend
cd web/frontend && npm install && npm run build
```

Deploy `StS2Tracker/bin/StS2Tracker.dll` to `<game>/mods/StS2Tracker/` and copy `web/frontend/dist/` contents to `<game>/mods/StS2Tracker/web/`.

## Known issues

- **Multiplayer victory summary**: The top-5 damage cards shown per player are aggregated across all players instead of being per-player.
