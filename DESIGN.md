# StS2 Run Tracker - Design Document

## Overview

A mod + web service for Slay the Spire 2 that captures detailed per-player combat
data beyond what the base game records, and hosts shareable run pages. One player
runs the mod; everyone in the session gets a link.

The game is Godot 4.5.1 + C#/.NET 9.0, ships with Harmony 2.4.2 and has official
mod support (`ModManager`, `ModInitializerAttribute`, Steam Workshop). Save files
are plain JSON. Combat state is synced to all clients in multiplayer, so the mod
works on any player (host or client).

---

## MVP (Phase 1) - Singleplayer Proof of Concept

### Goal
Prove we can hook into the combat system, capture data the base game doesn't save,
and display it meaningfully.

### What the base game already saves (per player, per floor)
- damage_taken, hp, max_hp, gold (gained/spent/stolen)
- card choices (offered + picked), relic choices, potion choices
- encounter ID, monster IDs, turns taken
- final deck, relics, potions
- win/loss, killed_by, seed, ascension, run_time

### What the mod adds (MVP)
- **Damage dealt** per player per combat (total, per-target)
- **Block gained** per player per combat
- **Cards played** per player per combat (count, sequence)
- **Powers applied** per player per combat (buffs/debuffs, stacks)
- **Per-turn breakdown** of the above (damage/block/cards per turn)

### Components

#### 1. C# Harmony Mod (`StS2Tracker`)
A .NET class library that loads via the game's mod system.

```
StS2Tracker/
  StS2Tracker.csproj        # targets net9.0, refs GodotSharp + 0Harmony + sts2.dll
  StS2Tracker.json          # mod manifest (name, version, description)
  mod_image.png             # mod icon
  src/
    ModEntry.cs             # [ModInitializer] entry point, sets up Harmony patches
    Patches/
      CombatPatches.cs      # hooks for damage/block/card/power/turn events
    Tracking/
      CombatTracker.cs      # accumulates per-combat stats in memory
      RunTracker.cs          # aggregates combat stats across the run
    Export/
      JsonExporter.cs       # writes enriched run data to JSON on combat end + run end
```

**Key Harmony hooks (to be confirmed via decompilation):**

| Event                      | What we capture                                  |
|----------------------------|--------------------------------------------------|
| `AfterDamageGiven`         | source creature, target, amount, was_blocked     |
| `AfterDamageReceived`      | target creature, amount, source                  |
| `AfterBlockGained`         | creature, amount                                 |
| `AfterCardPlayed`          | player, card ID, target, turn number             |
| `AfterPowerApplied`        | target creature, power ID, stacks, source        |
| `AfterPowerRemoved`        | creature, power ID                               |
| `AfterPlayerTurnStart`     | player ID, turn number                           |
| `AfterPlayerEndedTurn`     | player ID, turn number                           |
| `BeforeCombatStart`        | encounter ID, monster IDs - init tracker         |
| `AfterCombatEnd`           | win/loss - flush combat data                     |

**Output format:** JSON file written alongside the game's own save files.
Path: `%APPDATA%/SlayTheSpire2/tracker/<seed>_<timestamp>.json`

```json
{
  "mod_version": "0.1.0",
  "game_version": "v0.99.1",
  "seed": "4X0RR3BR28",
  "start_time": 1773259170,
  "player": {
    "steam_id": "76561198036923077",
    "character": "CHARACTER.DEFECT"
  },
  "combats": [
    {
      "floor": 2,
      "encounter": "ENCOUNTER.TOADPOLES_WEAK",
      "monsters": ["MONSTER.TOADPOLE", "MONSTER.TOADPOLE"],
      "turns": 3,
      "result": "win",
      "players": {
        "76561198036923077": {
          "damage_dealt": 47,
          "damage_taken": 4,
          "block_gained": 15,
          "cards_played": 8,
          "damage_per_turn": [18, 15, 14],
          "block_per_turn": [5, 5, 5],
          "cards_played_per_turn": [3, 3, 2],
          "card_play_sequence": [
            {"card": "CARD.STRIKE_DEFECT", "target": "MONSTER.TOADPOLE", "turn": 1},
            {"card": "CARD.DEFEND_DEFECT", "target": null, "turn": 1}
          ],
          "powers_applied": [
            {"power": "POWER.FOCUS", "stacks": 1, "turn": 2}
          ],
          "damage_by_target": {
            "MONSTER.TOADPOLE_0": 25,
            "MONSTER.TOADPOLE_1": 22
          }
        }
      }
    }
  ]
}
```

#### 2. Python Analyzer (already built: `sts2_tracker.py`)
Reads both base game saves AND mod output JSONs. Already handles:
- Run history, character stats, card pick/win rates, encounter difficulty
- Floor-by-floor HP/damage/gold charts
- Multiplayer per-player comparisons
- Architect damage tracking
- Live file watching

MVP additions:
- Parse mod combat JSONs and merge with base game save data
- Display per-combat damage dealt/block/cards breakdown
- Show damage dealt vs damage taken per floor

#### 3. Decompilation tooling
Install ILSpy CLI to decompile `sts2.dll` and confirm exact method signatures
for all hooks. This is a prerequisite for writing correct Harmony patches.

### MVP Test Plan
1. Install .NET 9 SDK
2. Install ILSpy CLI, decompile sts2.dll
3. Identify exact signatures for target hooks
4. Scaffold the mod project referencing game DLLs
5. Implement `BeforeCombatStart` + `AfterCombatEnd` hooks first (simplest lifecycle)
6. Add `AfterCardPlayed` hook (most visible - can verify via game log comparison)
7. Add damage/block hooks
8. Test in singleplayer: run a few floors, compare mod output vs game logs
9. Iterate on data accuracy

---

## Phase 2 - Multiplayer + Web Backend

### Goal
Capture all-player data in multiplayer, upload to a web service, generate shareable
run pages.

### Multiplayer mod changes
- Track all players (the game syncs combat state to every client, so hooks fire
  for all players regardless of who runs the mod)
- Player identification via Steam ID (already present in all game data)
- Per-player damage/block/card stats in the same combat JSON structure

### Multiplayer concerns to investigate
- **Confirm hooks fire for all players on a client** (not just host)
- **Indirect damage attribution:** orb damage (Defect), poison ticks (Silent),
  minion damage (Necrobinder), thorns - which creature is the "source"?
- **Timing:** do `AfterDamageGiven` events arrive in order on clients?

### Web Backend

Simple service - receives JSON, stores it, serves pages.

```
Backend/
  server.py              # FastAPI or Flask
  models.py              # run/combat data models
  storage.py             # SQLite or filesystem JSON store
  templates/
    run.html             # shareable run page
    combat.html           # combat detail view
```

**Endpoints:**
```
POST /api/runs                  # upload run data from mod
GET  /api/runs/<run_id>         # get run data as JSON
GET  /runs/<run_id>             # rendered run page (shareable link)
```

**Run page shows:**
- Run overview: character(s), seed, result, ascension, time
- Floor-by-floor timeline with HP/damage/gold
- Per-combat expandable details: damage dealt/taken per player, cards played,
  turns taken, powers in play
- Deck evolution over the run
- Multiplayer leaderboard per run (who dealt most damage, took least, etc.)

**Upload flow:**
1. Mod writes JSON locally after each combat + on run end
2. On run end, mod POSTs the full run JSON to the backend
3. Backend returns a run URL
4. Mod displays the URL in-game (via game log or a simple notification)
5. Player shares the link with friends

### Multiplayer UX
- One player has the mod installed
- After the run, they get a link like `https://sts2tracker.example.com/runs/abc123`
- Link shows all 4 players' stats, damage dealt, etc.
- Other players don't need the mod installed to view the page

---

## Phase 3+ (Future / Nice to Have)

- **In-game overlay:** post-combat stats screen showing damage dealt/taken per player
  (requires hooking into the game's UI system - `NHoverTipSet`, `CreateHoverTips`)
- **Card description overlay:** add win rate / pick rate stats to card hover tooltips
- **Real-time combat dashboard:** WebSocket-based live view during combat
- **Community aggregated stats:** card win rates across all uploaded runs
- **Steam Workshop distribution**
- **Architect damage leaderboard** (per-player contribution tracking)
- **Run comparison tool:** compare two runs side by side
- **Deck archetype detection:** auto-classify deck strategies

---

## Technical Details

### Game internals reference

| Thing | Location / Name |
|---|---|
| Game assembly | `data_sts2_windows_x86_64/sts2.dll` (8.9MB, .NET 9.0) |
| Harmony | `data_sts2_windows_x86_64/0Harmony.dll` (v2.4.2) |
| Mod system | `MegaCrit.Sts2.Core.Modding.ModManager` |
| Mod entry point | `[ModInitializerAttribute]` on a static method |
| Mod manifest | JSON file (name, version, desc) read by `ReadModManifest` |
| Combat manager | `MegaCrit.Sts2.Core.Combat.CombatManager` |
| Combat state | `MegaCrit.Sts2.Core.Combat.CombatState` |
| Creature base | `MegaCrit.Sts2.Core.Entities.Creatures.Creature` |
| Damage structures | `DamageProps`, `DamageCalc`, `DamageResult`, `AttackContext` |
| Save manager | `MegaCrit.Sts2.Core.Saves.SaveManager` |
| Run history | `MegaCrit.Sts2.Core.Runs.RunHistory` |
| Metrics uploader | `MegaCrit.Sts2.GameInfo.NGameInfoUploader` |
| Player IDs | Steam IDs (e.g. `76561198036923077`) in both saves and logs |

### Save file locations

| File | Path | Format |
|---|---|---|
| Run history | `Steam/userdata/<uid>/2868840/remote/profile1/saves/history/*.run` | JSON |
| Current run | `Steam/userdata/<uid>/2868840/remote/profile1/saves/current_run.save` | JSON |
| Progress | `Steam/userdata/<uid>/2868840/remote/profile1/saves/progress.save` | JSON |
| Settings | `Steam/userdata/<uid>/2868840/remote/settings.save` | JSON |
| Game logs | `%APPDATA%/SlayTheSpire2/logs/godot*.log` | Text |

### Multiplayer networking
- P2P via Steam networking (`SteamClientConnectionInitializer`)
- Host-authoritative: host runs combat logic, syncs via `CombatStateSynchronizer`
- All clients receive full combat state (card plays, damage, powers, etc.)
- Player actions sent to host via `ActionQueueSynchronizer`
- Messages typed: `RewardObtainedMessage`, `HandleEndTurnPingMessage`, etc.

### Metrics API (game's own)
- `POST https://sts2-metric-uploads.herokuapp.com/record_data/` (run data)
- `POST https://sts2-metric-uploads.herokuapp.com/record_achievement/`
- `POST https://sts2-metric-uploads.herokuapp.com/record_epoch/`
- `POST https://sts2-metric-uploads.herokuapp.com/record_settings/`
- Architect damage: Steam Stats global stat (read at game start)
- Rate limited (429 TooManyRequests observed)

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Game updates break Harmony patches | Mod crashes or silently fails | Document all hooked methods clearly; wrap patches in try/catch; version-check on load |
| Method signatures differ from what string extraction suggests | Patches don't compile or hook wrong methods | Decompile with ILSpy first; this is a hard prereq |
| Modded runs flagged differently | Leaderboard exclusion, metrics not uploaded | Acceptable for a tracker tool; investigate `_runningModded` flag |
| Client-side hooks miss events in multiplayer | Incomplete data for non-host players | Test explicitly; fall back to host-only if needed |
| Indirect damage attribution unclear | Incorrect per-player damage totals | Investigate in decompiled code; test with each character |
| Early Access = rapid change | Frequent maintenance needed | Keep mod minimal; document hook targets for easy updates |

---

## Development Steps (ordered)

### Phase 1 (MVP)
1. Install .NET 9 SDK + ILSpy CLI
2. Decompile `sts2.dll`, document target method signatures
3. Fetch example mod wiki, understand manifest + build setup
4. Scaffold mod project with correct references
5. Implement lifecycle hooks (combat start/end) - verify mod loads
6. Add `AfterCardPlayed` hook - verify against game logs
7. Add damage/block hooks
8. Add power tracking hooks
9. Wire up JSON export
10. Extend Python analyzer to read mod data
11. Singleplayer end-to-end test

### Phase 2 (Multiplayer + Web)
12. Test mod in multiplayer (confirm all-player visibility)
13. Handle multi-player combat JSON structure
14. Build web backend (FastAPI + SQLite)
15. Add upload from mod on run end
16. Build run page template
17. Multiplayer end-to-end test

### Phase 3 (Privacy, Upload Settings, Community)

#### Mod Settings UI (in-game or config file)

**Upload scope:**
- All Historical Data / New Data Only (retroactively upload existing runs or start fresh)
- Multiplayer Only / Single + Multi (some players may only want to share MP data)
- Fully Anonymized mode (strip Steam IDs, replace with random hashes per run)

**Visibility:**
- Public (anyone with link can see)
- Friends Only (only Steam friends can view)
- Private (only you, via authenticated dashboard)

#### Steam Friends-Only Visibility

Requires Steam Web API integration on the backend:
- Player authenticates via Steam OpenID on the web dashboard
- Backend calls Steam `GetFriendList` API to check if viewer is friends with
  the run owner
- Run pages return 403 if not friends
- The mod itself doesn't need to do auth - it just tags runs with the player's
  Steam ID. Auth happens server-side when someone tries to view.
- Steam Web API key required on the server (free from Steamworks partner site)
- Not super hard, but adds a real auth layer. Could start with "public or
  private" toggle and add friends-only later.

#### Community Aggregate Stats

With enough uploaded data, the service can show:
- Global card pick rates and win rates (across all players)
- Encounter difficulty rankings from real combat data (damage taken, turns)
- Character win rates by ascension level
- Popular deck archetypes / card combinations
- "How does your run compare to average?"
- Best single hits across all players (leaderboard)

All aggregate stats can use anonymized data - no need for player identity.

### Phase 4+ (Polish)
18. In-game overlay / post-combat stats
19. Steam Workshop packaging
20. Card tooltip enhancements
