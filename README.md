# StS2 Run Tracker

A mod for Slay the Spire 2 that captures detailed per-player combat stats
(damage dealt, block, cards played, kills) and exports them as JSON.
Includes a live terminal dashboard and a Python analyzer for historical data.

## Install

1. Copy the `StS2Tracker` folder into the game's mods directory:
   ```
   C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\mods\StS2Tracker\
   ```
   It should contain:
   ```
   StS2Tracker.json    (mod manifest)
   StS2Tracker.dll     (mod code)
   ```

2. Launch Slay the Spire 2.

3. **First time only:** The game will show a mod loading confirmation popup.
   Accept it. The game will quit - this is normal. Relaunch the game.

4. On the second launch, the mod loads automatically. You'll see
   `[StS2Tracker]` messages in the game log confirming it's running.

### Modded Save Profile

The game uses a **separate save profile** when mods are loaded. Your normal
(unmodded) progress is untouched, but modded mode starts with a fresh profile.
Save paths:
```
profile1/           -> unmodded saves
modded/profile1/    -> modded saves
```
This is the game's built-in behavior, not something the mod does. To go back
to your normal saves, just remove or rename the `mods/` folder and relaunch.

## Usage

### Live Dashboard

Run in a separate terminal while playing:
```
py live_tracker.py
```
Shows real-time combat stats as you play: damage dealt/taken per player,
block, cards played, per-turn breakdowns, and recent card sequences.
Updates after each combat ends.

### Run Analyzer

Analyze all your historical run data (works without the mod - reads base game saves):
```
py sts2_tracker.py summary       # overall stats
py sts2_tracker.py characters    # per-character breakdown
py sts2_tracker.py cards         # card pick/win rates
py sts2_tracker.py encounters    # hardest encounters
py sts2_tracker.py runs          # list all runs
py sts2_tracker.py run -r -1     # latest run floor-by-floor detail
py sts2_tracker.py multiplayer   # per-player multiplayer stats
py sts2_tracker.py architect     # architect damage over time
py sts2_tracker.py all           # everything
```

## What the Mod Tracks

Data the base game does NOT save, captured via Harmony hooks:

| Stat | Per-player | Per-turn | Per-target |
|------|-----------|----------|------------|
| Damage dealt | Yes | Yes | Yes |
| Damage taken | Yes | - | - |
| Damage blocked | Yes | - | - |
| Block gained | Yes | Yes | - |
| Cards played | Yes | Yes | - |
| Card play sequence | Yes | Yes (tagged) | Yes (tagged) |
| Kills | Yes | - | - |

Pet/minion damage is attributed to the owning player.

## Output

Tracker JSON is written to:
```
%APPDATA%\SlayTheSpire2\tracker\<seed>_<timestamp>.json
```

## Building from Source

Requires .NET 9 SDK.

```
cd StS2Tracker
dotnet build -p:STS2GameDir="C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2"
```

Then copy `StS2Tracker\bin\StS2Tracker.dll` to the game's `mods\StS2Tracker\` folder.

## Files

```
slaythespiredata/
  README.md                 # this file
  DESIGN.md                 # full design doc and roadmap
  HOOKS_REFERENCE.md        # decompiled game API reference
  live_tracker.py           # real-time terminal dashboard
  sts2_tracker.py           # historical run analyzer
  StS2Tracker/              # C# mod source
    StS2Tracker.json        # mod manifest
    StS2Tracker.csproj      # build config
    src/
      ModEntry.cs           # mod entry point
      CombatTracker.cs      # data collection + JSON export
      HarmonyPatches.cs     # Harmony hooks into game events
  decompiled/               # ILSpy output for reference
    full/                   # full project decompilation
    *.cs                    # individual key types
```
