# StS2 Tracker - Web Dashboard Spec

## Overview

A React + FastAPI dashboard that shows live combat data and historical run analysis
for Slay the Spire 2. The mod writes JSON after each combat; the server watches
for changes and pushes updates to connected clients via WebSocket.

## Data Sources

### 1. Mod Output (live combat data)
Path: `%APPDATA%/SlayTheSpire2/tracker/<seed>_<timestamp>.json`
Updated after every combat ends. Format:

```json
{
  "mod_version": "0.1.0",
  "seed": "PQ67225W5M",
  "start_time": 1774219976,
  "combats": [
    {
      "encounter": "ENCOUNTER.NIBBITS_WEAK",
      "monsters": ["MONSTER.NIBBIT"],
      "floor_index": 1,
      "total_turns": 3,
      "result": "win",
      "players": {
        "1": {
          "steam_id": "1",
          "character": "CHARACTER.IRONCLAD",
          "damage_dealt": 50,
          "damage_taken": 13,
          "damage_blocked": 5,
          "block_gained": 5,
          "cards_played": 8,
          "kills": 1,
          "damage_per_turn": [12, 14, 24],
          "block_per_turn": [5, 0, 0],
          "cards_per_turn": [3, 2, 3],
          "card_sequence": [
            {"card": "CARD.STRIKE_IRONCLAD", "target": "MONSTER.NIBBIT", "turn": 1},
            {"card": "CARD.STRIKE_IRONCLAD", "target": "MONSTER.NIBBIT", "turn": 1},
            {"card": "CARD.DEFEND_IRONCLAD", "target": null, "turn": 1},
            {"card": "CARD.STRIKE_IRONCLAD", "target": "MONSTER.NIBBIT", "turn": 2},
            {"card": "CARD.BASH", "target": "MONSTER.NIBBIT", "turn": 2},
            {"card": "CARD.STRIKE_IRONCLAD", "target": "MONSTER.NIBBIT", "turn": 3},
            {"card": "CARD.STRIKE_IRONCLAD", "target": "MONSTER.NIBBIT", "turn": 3},
            {"card": "CARD.STRIKE_IRONCLAD", "target": "MONSTER.NIBBIT", "turn": 3}
          ],
          "damage_by_target": {"MONSTER.NIBBIT": 50},
          "damage_by_card": {
            "CARD.STRIKE_IRONCLAD": {"total_damage": 36, "hits": 6, "max_hit": 9, "kills": 0},
            "CARD.BASH": {"total_damage": 14, "hits": 1, "max_hit": 14, "kills": 1}
          }
        }
      }
    }
  ]
}
```

### 2. Game Save Files (historical run data)
Path: `Steam/userdata/<uid>/2868840/remote/profile1/saves/history/*.run`
These are plain JSON. Each file is a completed run. Format (abbreviated):

```json
{
  "acts": ["ACT.OVERGROWTH", "ACT.HIVE", "ACT.GLORY"],
  "ascension": 1,
  "build_id": "v0.98.3",
  "game_mode": "standard",
  "killed_by_encounter": "ENCOUNTER.KNOWLEDGE_DEMON_BOSS",
  "killed_by_event": "NONE.NONE",
  "seed": "4X0RR3BR28",
  "start_time": 1773259170,
  "run_time": 3299,
  "win": false,
  "was_abandoned": false,
  "platform_type": "steam",
  "players": [
    {
      "id": 76561198036923077,
      "character": "CHARACTER.NECROBINDER",
      "deck": [
        {"id": "CARD.STRIKE_NECROBINDER", "current_upgrade_level": 1, "floor_added_to_deck": 1}
      ],
      "relics": [
        {"id": "RELIC.BOUND_PHYLACTERY", "floor_added_to_deck": 1}
      ],
      "potions": [
        {"id": "POTION.VULNERABLE_POTION", "slot_index": 0}
      ],
      "max_potion_slot_count": 3
    }
  ],
  "map_point_history": [
    [
      {
        "map_point_type": "ancient",
        "player_stats": [
          {
            "player_id": 1,
            "current_hp": 66, "max_hp": 66,
            "damage_taken": 0, "hp_healed": 66,
            "current_gold": 99, "gold_gained": 0, "gold_spent": 0,
            "card_choices": [
              {"card": {"id": "CARD.PULL_AGGRO"}, "was_picked": true},
              {"card": {"id": "CARD.CALCIFY"}, "was_picked": false}
            ],
            "relic_choices": [
              {"choice": "RELIC.ARCANE_SCROLL", "was_picked": true}
            ]
          }
        ],
        "rooms": [
          {
            "model_id": "EVENT.NEOW",
            "room_type": "event",
            "turns_taken": 0
          }
        ]
      }
    ]
  ]
}
```

Multiplayer runs have multiple entries in `players` (with Steam IDs as `id`) and
multiple entries per `player_stats` array per floor.

### 3. Progress Save (lifetime stats)
Path: `Steam/userdata/<uid>/2868840/remote/profile1/saves/progress.save`

Contains per-character stats (wins, losses, streaks, playtime, max ascension),
per-card stats (times_picked, times_skipped, times_won, times_lost),
per-encounter stats (wins/losses per character), and discovery lists.

## Architecture

```
slaythespiredata/
  web/
    server/
      main.py             # FastAPI app
      watcher.py           # watches tracker JSON + save files for changes
      models.py            # pydantic models for the data
    frontend/
      src/
        App.tsx
        components/
          LiveRun.tsx       # current run live view
          CombatDetail.tsx  # single combat breakdown
          RunHistory.tsx    # historical run list
          RunDetail.tsx     # single historical run detail
          PlayerCard.tsx    # per-player stat card
          DamageChart.tsx   # damage charts/bars
          CardStats.tsx     # per-card damage breakdown
        hooks/
          useWebSocket.ts   # live data subscription
```

## Server (FastAPI)

### Endpoints
```
GET  /api/live              # current tracker JSON (latest file)
GET  /api/runs              # list all historical runs (summary)
GET  /api/runs/<filename>   # single run detail
GET  /api/progress          # lifetime stats from progress.save
WS   /ws                    # WebSocket - pushes updates when tracker file changes
```

### WebSocket behavior
- Server watches `%APPDATA%/SlayTheSpire2/tracker/` for file changes
- On change, reads the JSON and pushes to all connected WebSocket clients
- Message format: `{"type": "combat_update", "data": <full tracker JSON>}`

## Frontend (React)

### Pages / Views

#### 1. Live Run Dashboard (`/`)
The main view when playing. Shows:

**Header bar:**
- Seed, character name, run status (in progress / completed)
- Total combats, total damage dealt, current floor

**Run timeline:**
- Horizontal bar showing each combat as a node
- Color-coded by result (green=win, red=loss)
- Click to expand combat detail

**Current/Latest Combat panel:**
- Encounter name, monsters, turns taken, result
- Per-player stat cards (see PlayerCard below)
- Per-turn damage/block chart (bar chart, one bar per turn)
- Card play sequence (horizontal timeline of card icons/names)

**Run Totals sidebar:**
- Cumulative damage dealt / taken / blocked per player
- Cards played total
- Kills total
- Best single hit (card name + damage)

#### 2. Combat Detail (expandable or `/combat/<index>`)
- Encounter name + monsters
- Per-player:
  - Damage dealt (total + bar)
  - Damage taken (total + bar)
  - Block gained
  - Cards played count
  - **damage_by_card table**: card name, total damage, hits, max hit, kills
    Sorted by total damage descending. Highlight the biggest single hit.
  - **damage_by_target**: which monsters took how much
  - **Per-turn breakdown**: bar chart of damage/block/cards per turn
  - **Card sequence**: ordered list of cards played with turn markers

#### 3. Run History (`/history`)
- Table of all completed runs from save files
- Columns: date, character, ascension, result (W/L), run time, seed, floors
- Click to expand full run detail
- Filter by character, result, ascension

#### 4. Run Detail (`/history/<run>`)
- Floor-by-floor timeline showing:
  - Room type (monster/elite/boss/event/shop/rest/treasure)
  - HP after floor (bar chart)
  - Damage taken
  - Gold
  - Cards/relics picked
- Final deck, relics, potions
- Killed by (if loss)

#### 5. Stats Overview (`/stats`)
- Per-character: win rate, games played, best streak, avg run time
- Top cards by pick rate and win rate
- Hardest encounters
- Total playtime

### PlayerCard Component
A reusable card showing one player's combat stats:
```
+----------------------------------+
| IRONCLAD (Player 1)             |
|                                  |
| Damage Dealt: 50  ████████████  |
| Damage Taken: 13  ███           |
| Block Gained:  5  █             |
| Cards Played:  8                |
| Kills: 1                        |
|                                  |
| Top Cards:                       |
| Strike   36 dmg (6x, max 9)    |
| Bash     14 dmg (1x, max 14)*  |
|              * = killing blow    |
+----------------------------------+
```

### Design notes
- Dark theme (the game is dark-themed)
- Use warm amber/gold accents (matches StS aesthetic)
- Cards and relics referenced by their game IDs - display with the portion
  after the dot, replacing underscores with spaces, title-cased
  (e.g. "CARD.STRIKE_IRONCLAD" -> "Strike Ironclad")
- Responsive - works on a second monitor or phone
- Auto-refresh via WebSocket, no manual polling needed

## Helper: ID formatting
All game IDs follow the pattern `TYPE.NAME_WITH_UNDERSCORES`. To display:
1. Split on first `.` to get the name portion
2. Replace `_` with spaces
3. Title case
Example: `ENCOUNTER.NIBBITS_WEAK` -> `Nibbits Weak`

## File paths (Windows)
- Tracker JSON: `%APPDATA%\SlayTheSpire2\tracker\`
- Save directory: `%APPDATA%\SlayTheSpire2\steam\<steam64id>\` (auto-discovered)
- Save history: `<save_dir>\modded\profile1\saves\history\` (or `profile1\saves\history\` for unmodded)
- Progress save: `<save_dir>\modded\profile1\saves\progress.save`

## Tech stack
- **Backend**: Python FastAPI, uvicorn, watchfiles (for file watching), websockets
- **Frontend**: React 18+ with TypeScript, Vite, Tailwind CSS, recharts (for charts)
- **Deployment**: Docker Compose - one container for backend, one for frontend (nginx serving built assets)
- The data directories (tracker JSON, save files) should be mounted as volumes
- Do NOT use emojis in Python due to Windows encoding issues

## Docker setup
```
web/
  docker-compose.yml
  server/
    Dockerfile
    main.py
    ...
  frontend/
    Dockerfile
    ...
```

`docker-compose.yml` should:
- Mount `%APPDATA%/SlayTheSpire2/tracker` into the backend container (read-only)
- Mount the Steam save directory into the backend container (read-only)
- Backend on port 8000 (API + WebSocket)
- Frontend on port 3000 (dev) or 80 (production nginx)
- Use environment variables for data paths so they're configurable
