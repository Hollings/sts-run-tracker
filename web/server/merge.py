"""
Data merge utility - combines mod tracker JSON (combat detail) with
game save files (card rewards, relics, events, HP, gold) into a
unified run view.

The mod tracks: damage dealt, block gained, per-card damage, card play
sequences, per-turn breakdowns.

The game save tracks: card/relic/potion choices, HP, gold, events,
rest site actions, deck contents, map path.

This module merges both into a single structure keyed by floor number.
"""

import json
import os
import glob
from typing import Optional

# Default paths - overridden by env vars or Docker volume mounts
TRACKER_DIR = os.environ.get(
    "STS2_TRACKER_DIR",
    os.path.join(os.environ.get("APPDATA", ""), "SlayTheSpire2", "tracker")
)
def _discover_save_dir() -> str:
    """Auto-discover the save directory for StS2.

    The game stores saves in two places:
    1. %APPDATA%/SlayTheSpire2/steam/<steam64id>/ (primary - game reads/writes here)
    2. Steam/userdata/<steam32id>/2868840/remote/ (cloud sync copy)
    We prefer #1 since that's what the game actually uses.
    """
    env_override = os.environ.get("STS2_SAVE_DIR")
    if env_override:
        return env_override
    # Primary: %APPDATA%/SlayTheSpire2/steam/<steam64id>/
    appdata_base = os.path.join(
        os.environ.get("APPDATA", ""), "SlayTheSpire2", "steam"
    )
    if os.path.isdir(appdata_base):
        candidates = []
        for steam_id in os.listdir(appdata_base):
            steam_dir = os.path.join(appdata_base, steam_id)
            if os.path.isdir(steam_dir):
                candidates.append(steam_dir)
        if candidates:
            if len(candidates) == 1:
                return candidates[0]
            return max(candidates, key=lambda d: os.path.getmtime(d))
    # Fallback: Steam userdata (cloud sync copy)
    steam_base = os.path.join(
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        "Steam", "userdata"
    )
    if os.path.isdir(steam_base):
        candidates = []
        for user_id in os.listdir(steam_base):
            remote_dir = os.path.join(steam_base, user_id, "2868840", "remote")
            if os.path.isdir(remote_dir):
                candidates.append(remote_dir)
        if candidates:
            if len(candidates) == 1:
                return candidates[0]
            return max(candidates, key=lambda d: os.path.getmtime(d))
    return os.path.join(appdata_base, "unknown")


SAVE_DIR = _discover_save_dir()


def short_id(full_id: str) -> str:
    """CARD.STRIKE_IRONCLAD -> Strike Ironclad"""
    if not full_id:
        return "?"
    if "." in full_id:
        full_id = full_id.split(".", 1)[1]
    return full_id.replace("_", " ").title()


def load_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return None


MODDED_SAVES = os.path.join(SAVE_DIR, "modded", "profile1", "saves")
UNMODDED_SAVES = os.path.join(SAVE_DIR, "profile1", "saves")


def get_save_profile_dir() -> str:
    """Return the active save profile dir (modded or unmodded).
    Called dynamically each time - prefers modded if it has any data."""
    # Prefer modded if it has a current run OR history
    if os.path.exists(os.path.join(MODDED_SAVES, "current_run.save")):
        return MODDED_SAVES
    if os.path.isdir(os.path.join(MODDED_SAVES, "history")):
        return MODDED_SAVES
    return UNMODDED_SAVES


# --- Tracker data ---

def get_latest_tracker_file() -> Optional[str]:
    if not os.path.isdir(TRACKER_DIR):
        return None
    files = glob.glob(os.path.join(TRACKER_DIR, "*.json"))
    return max(files, key=os.path.getmtime) if files else None


def get_all_tracker_files() -> list[str]:
    if not os.path.isdir(TRACKER_DIR):
        return []
    return sorted(glob.glob(os.path.join(TRACKER_DIR, "*.json")),
                  key=os.path.getmtime, reverse=True)


def load_tracker(path: str) -> Optional[dict]:
    return load_json(path)


# --- Game save data ---

def load_current_or_latest_run() -> Optional[dict]:
    """Load active run, or fall back to the most recent completed run.
    Prefers the most recently modified save between current_run.save and
    current_run_mp.save (multiplayer uses a separate file)."""
    save_dir = get_save_profile_dir()
    # Check both singleplayer and multiplayer save files, prefer most recent
    candidates = []
    for name in ("current_run.save", "current_run_mp.save"):
        path = os.path.join(save_dir, name)
        if os.path.exists(path):
            candidates.append(path)
    if candidates:
        best = max(candidates, key=os.path.getmtime)
        return load_json(best)
    # No active run - load the latest completed run from history
    history_dir = os.path.join(save_dir, "history")
    if os.path.isdir(history_dir):
        runs = sorted(glob.glob(os.path.join(history_dir, "*.run")),
                      key=os.path.getmtime, reverse=True)
        if runs:
            return load_json(runs[0])
    return None


# Keep old name as alias for backward compat
load_current_run = load_current_or_latest_run


def load_progress() -> Optional[dict]:
    save_dir = get_save_profile_dir()
    path = os.path.join(save_dir, "progress.save")
    return load_json(path)


def load_run_history() -> list[dict]:
    """Load all completed run files from history."""
    save_dir = get_save_profile_dir()
    history_dir = os.path.join(save_dir, "history")
    runs = []
    if not os.path.isdir(history_dir):
        # Also check unmodded profile
        unmodded_history = os.path.join(SAVE_DIR, "profile1", "saves", "history")
        if os.path.isdir(unmodded_history):
            history_dir = unmodded_history
        else:
            return []
    for path in sorted(glob.glob(os.path.join(history_dir, "*.run")),
                       key=os.path.getmtime, reverse=True):
        data = load_json(path)
        if data:
            data["_filename"] = os.path.basename(path)
            runs.append(data)
    return runs


def get_run_summary(run: dict) -> dict:
    """Extract a compact summary from a run file."""
    players = run.get("players", [])
    return {
        "filename": run.get("_filename", ""),
        "seed": run.get("seed", ""),
        "start_time": run.get("start_time", 0),
        "run_time": run.get("run_time", 0),
        "ascension": run.get("ascension", 0),
        "win": run.get("win", False),
        "was_abandoned": run.get("was_abandoned", False),
        "killed_by": short_id(run.get("killed_by_encounter", "")),
        "game_mode": run.get("game_mode", "standard"),
        "acts": [short_id(a) for a in run.get("acts", [])],
        "players": [
            {
                "id": str(p.get("id", "")),
                "character": short_id(p.get("character", "")),
                "deck_size": len(p.get("deck", [])),
                "relic_count": len(p.get("relics", [])),
            }
            for p in players
        ],
    }


# --- Merge logic ---

def merge_live_run(tracker: Optional[dict], save: Optional[dict]) -> dict:
    """
    Merge tracker combat data with game save data into a unified run view.

    The save file has floor-by-floor data in map_point_history.
    The tracker has per-combat detail.

    We produce a single timeline of floors, each with:
    - Base data from save (hp, gold, card choices, room type, etc.)
    - Combat detail from tracker (damage dealt, block, card sequences, etc.)
    """
    result = {
        "run_info": {},
        "floors": [],
        "combats": [],
        "run_totals": {},
    }

    matched_combats: set[int] = set()

    # Run info from tracker
    if tracker:
        result["run_info"] = tracker.get("run_info", {})
        result["combats"] = tracker.get("combats", [])

    # Discard save data if it belongs to a different run (stale save file)
    if save and tracker:
        tracker_seed = tracker.get("run_info", {}).get("seed", "")
        save_seed = save.get("seed", "")
        if tracker_seed and save_seed and tracker_seed != save_seed:
            save = None
        elif tracker_seed and not save_seed:
            # Save has no seed (e.g. old MP save with null seed) - check timestamps
            tracker_start = tracker.get("run_info", {}).get("start_time", 0)
            save_start = save.get("start_time", 0)
            if tracker_start and save_start and abs(tracker_start - save_start) > 3600:
                save = None

    # Build floor timeline from save
    if save:
        # Overlay run info from save if tracker didn't have it
        if not result["run_info"]:
            players = save.get("players", [])
            result["run_info"] = {
                "seed": save.get("seed", ""),
                "ascension": save.get("ascension", 0),
                "players": [
                    {"steam_id": str(p.get("id", "")),
                     "character": p.get("character", "")}
                    for p in players
                ],
            }

        floor_num = 0
        for act_idx, act in enumerate(save.get("map_point_history", [])):
            if not isinstance(act, list):
                continue
            for mp in act:
                floor_num += 1
                floor = _build_floor(mp, floor_num, act_idx)

                # Try to match combat data from tracker
                if tracker and floor["type"] in ("monster", "elite", "boss", "event", "unknown"):
                    mp_rooms = mp.get("rooms", [])
                    room_model = mp_rooms[0].get("model_id", "") if mp_rooms else ""
                    for ci, combat in enumerate(tracker.get("combats", [])):
                        if ci in matched_combats:
                            continue
                        # Match by floor number first
                        if combat.get("floor") == floor_num:
                            floor["combat"] = combat
                            matched_combats.add(ci)
                            break
                    else:
                        # Fall back to matching by encounter name (second pass)
                        for ci, combat in enumerate(tracker.get("combats", [])):
                            if ci in matched_combats:
                                continue
                            if room_model and combat.get("encounter") == room_model:
                                floor["combat"] = combat
                                matched_combats.add(ci)
                                break

                result["floors"].append(floor)

    # Inject synthetic floors for tracker combats on floors the save file
    # hasn't recorded yet (e.g. in-progress combat)
    if tracker:
        existing_floors = {f["floor"] for f in result["floors"]}
        seen_synthetic = set()
        for combat in tracker.get("combats", []):
            combat_floor = combat.get("floor", 0)
            if combat_floor in existing_floors or combat_floor in seen_synthetic:
                continue
            seen_synthetic.add(combat_floor)
            # Build a minimal floor from tracker combat data
            floor_num = combat.get("floor", len(result["floors"]) + 1)
            encounter = combat.get("encounter", "")
            # Determine floor type from encounter name heuristics
            enc_lower = encounter.lower()
            if "boss" in enc_lower:
                floor_type = "boss"
            elif "elite" in enc_lower:
                floor_type = "elite"
            else:
                floor_type = "monster"
            synthetic = {
                "floor": floor_num,
                "act": (result["floors"][-1]["act"] if result["floors"] else 1),
                "type": floor_type,
                "room_id": short_id(encounter),
                "room_type": floor_type,
                "turns_taken": combat.get("total_turns", 0),
                "monsters": [short_id(m) for m in combat.get("monsters", [])],
                "players": [
                    {
                        "player_id": pid,
                        "hp": 0,
                        "max_hp": 0,
                        "damage_taken": stats.get("damage_taken", 0),
                        "hp_healed": 0,
                        "gold": 0,
                        "gold_gained": 0,
                        "gold_spent": 0,
                        "cards_picked": [],
                        "cards_skipped": [],
                        "relics_picked": [],
                        "potions_picked": [],
                        "event_choices": [],
                    }
                    for pid, stats in combat.get("players", {}).items()
                ],
                "combat": combat,
            }
            result["floors"].append(synthetic)

    # Compute run totals from tracker combats
    if result["combats"]:
        result["run_totals"] = _compute_run_totals(result["combats"])

    return result


ROOM_TYPE_NAMES = {
    "rest_site": "Rest Site",
    "treasure": "Treasure",
    "shop": "Shop",
    "event": "Event",
    "unknown": "Event",
    "ancient": "Ancient",
    "monster": "Monster",
    "elite": "Elite",
    "boss": "Boss",
}


def _parse_event_choice(key: str) -> str:
    """Parse event localization key into readable name.
    e.g. 'BUGSLAYER.pages.INITIAL.options.EXTERMINATION.title' -> 'Extermination'
         'POMANDER.title' -> 'Pomander'
    """
    if not key:
        return ""
    parts = key.split(".")
    # Pattern: EVENT.pages.PAGE.options.CHOICE.title
    if "options" in parts:
        idx = parts.index("options")
        if idx + 1 < len(parts):
            return parts[idx + 1].replace("_", " ").title()
    # Fallback: use first part
    return parts[0].replace("_", " ").title()


def _build_floor(mp: dict, floor_num: int, act_idx: int) -> dict:
    """Build a floor entry from a map_point_history entry."""
    rooms = mp.get("rooms", [])
    room = rooms[0] if rooms else {}

    floor = {
        "floor": floor_num,
        "act": act_idx + 1,
        "type": mp.get("map_point_type", "unknown"),
        "room_id": short_id(room.get("model_id", "")) or ROOM_TYPE_NAMES.get(mp.get("map_point_type", ""), mp.get("map_point_type", "?")),
        "room_type": room.get("room_type", ""),
        "turns_taken": room.get("turns_taken", 0),
        "monsters": [short_id(m) for m in room.get("monster_ids", [])],
        "players": [],
    }

    for ps in mp.get("player_stats", []):
        player_floor = {
            "player_id": str(ps.get("player_id", "")),
            "hp": ps.get("current_hp", 0),
            "max_hp": ps.get("max_hp", 0),
            "damage_taken": ps.get("damage_taken", 0),
            "hp_healed": ps.get("hp_healed", 0),
            "gold": ps.get("current_gold", 0),
            "gold_gained": ps.get("gold_gained", 0),
            "gold_spent": ps.get("gold_spent", 0),
            "cards_picked": [],
            "cards_skipped": [],
            "relics_picked": [],
            "potions_picked": [],
        }

        # Card choices
        for cc in ps.get("card_choices", []):
            card_id = cc.get("card", {}).get("id", "")
            if cc.get("was_picked"):
                player_floor["cards_picked"].append(short_id(card_id))
            else:
                player_floor["cards_skipped"].append(short_id(card_id))

        # Relic choices
        for rc in ps.get("relic_choices", []):
            if rc.get("was_picked"):
                player_floor["relics_picked"].append(short_id(rc.get("choice", "")))

        # Potion choices
        for pc in ps.get("potion_choices", []):
            if pc.get("was_picked"):
                player_floor["potions_picked"].append(short_id(pc.get("choice", "")))

        # Event choices - parse localization keys into readable names
        # e.g. "BUGSLAYER.pages.INITIAL.options.EXTERMINATION.title" -> "Extermination"
        player_floor["event_choices"] = [
            _parse_event_choice(ec.get("title", {}).get("key", ""))
            for ec in ps.get("event_choices", [])
        ]

        # Rest site actions
        player_floor["rest_site_choices"] = [
            s.title() for s in ps.get("rest_site_choices", [])
        ]
        player_floor["upgraded_cards"] = [
            short_id(c) for c in ps.get("upgraded_cards", [])
        ]

        floor["players"].append(player_floor)

    return floor


def _compute_run_totals(combats: list[dict]) -> dict:
    """Aggregate combat stats across a full run."""
    player_totals: dict[str, dict] = {}

    for combat in combats:
        for pid, stats in combat.get("players", {}).items():
            if pid not in player_totals:
                player_totals[pid] = {
                    "steam_id": pid,
                    "character": stats.get("character", ""),
                    "damage_dealt": 0,
                    "damage_taken": 0,
                    "damage_blocked": 0,
                    "block_gained": 0,
                    "cards_played": 0,
                    "kills": 0,
                    "combats": 0,
                    "best_hit": {"card": "", "damage": 0, "encounter": ""},
                    "damage_by_card": {},
                }
            t = player_totals[pid]
            t["damage_dealt"] += stats.get("damage_dealt", 0)
            t["damage_taken"] += stats.get("damage_taken", 0)
            t["damage_blocked"] += stats.get("damage_blocked", 0)
            t["block_gained"] += stats.get("block_gained", 0)
            t["cards_played"] += stats.get("cards_played", 0)
            t["kills"] += stats.get("kills", 0)
            t["combats"] += 1

            # Aggregate per-card damage and find best single hit
            for card_id, card_stats in stats.get("damage_by_card", {}).items():
                if card_id not in t["damage_by_card"]:
                    t["damage_by_card"][card_id] = {
                        "total_damage": 0, "hits": 0, "max_hit": 0, "kills": 0
                    }
                agg = t["damage_by_card"][card_id]
                agg["total_damage"] += card_stats.get("total_damage", 0)
                agg["hits"] += card_stats.get("hits", 0)
                agg["kills"] += card_stats.get("kills", 0)
                if card_stats.get("max_hit", 0) > agg["max_hit"]:
                    agg["max_hit"] = card_stats["max_hit"]

                # Track best single hit across the run
                if card_stats.get("max_hit", 0) > t["best_hit"]["damage"]:
                    t["best_hit"] = {
                        "card": short_id(card_id),
                        "damage": card_stats["max_hit"],
                        "encounter": short_id(combat.get("encounter", "")),
                    }

    return {
        "total_combats": len(combats),
        "wins": sum(1 for c in combats if c.get("result") == "win"),
        "losses": sum(1 for c in combats if c.get("result") == "loss"),
        "players": player_totals,
    }
