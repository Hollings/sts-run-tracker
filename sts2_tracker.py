"""
Slay the Spire 2 - Comprehensive Run Tracker & Analyzer

Reads save data from Steam userdata to provide:
- Run history analysis (win rates, character stats, card pick rates)
- Per-floor damage/HP/gold charts
- Multiplayer per-player comparisons
- Deck evolution tracking
- Encounter difficulty analysis
- Live run monitoring via file watching
- Architect damage tracking via Steam Stats
"""

import json
import os
import sys
import glob
import time
import argparse
from datetime import datetime, timezone
from collections import defaultdict, Counter
from pathlib import Path

# Avoid unicode errors on Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

STEAM_USERDATA = os.path.expandvars(
    r"%ProgramFiles(x86)%\Steam\userdata"
)
APPDATA_LOGS = os.path.join(os.environ.get("APPDATA", ""), "SlayTheSpire2", "logs")
GAME_APP_ID = "2868840"


def find_save_dir():
    """Auto-detect the StS2 save directory from Steam userdata."""
    for user_dir in glob.glob(os.path.join(STEAM_USERDATA, "*")):
        candidate = os.path.join(user_dir, GAME_APP_ID, "remote")
        if os.path.isdir(candidate):
            return candidate
    return None


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ts_to_str(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def short_id(full_id):
    """CARD.STRIKE_IRONCLAD -> Strike Ironclad"""
    if "." in full_id:
        full_id = full_id.split(".", 1)[1]
    return full_id.replace("_", " ").title()


def load_all_runs(save_dir):
    """Load all run history files."""
    profile_dir = os.path.join(save_dir, "profile1", "saves", "history")
    runs = []
    for path in sorted(glob.glob(os.path.join(profile_dir, "*.run"))):
        try:
            data = load_json(path)
            data["_filename"] = os.path.basename(path)
            runs.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load {path}: {e}")
    return runs


def load_progress(save_dir):
    path = os.path.join(save_dir, "profile1", "saves", "progress.save")
    if os.path.exists(path):
        return load_json(path)
    return None


def load_current_run(save_dir):
    path = os.path.join(save_dir, "profile1", "saves", "current_run.save")
    if os.path.exists(path):
        return load_json(path)
    return None


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def analyze_overall(runs, progress):
    """Print overall run statistics."""
    print("\n" + "=" * 60)
    print("  OVERALL STATISTICS")
    print("=" * 60)

    total = len(runs)
    wins = sum(1 for r in runs if r.get("win"))
    losses = total - wins
    abandoned = sum(1 for r in runs if r.get("was_abandoned"))

    print(f"\n  Total Runs:  {total}")
    print(f"  Wins:        {wins} ({wins/total*100:.1f}%)" if total else "")
    print(f"  Losses:      {losses - abandoned}")
    print(f"  Abandoned:   {abandoned}")

    if progress:
        print(f"\n  Total Playtime: {progress.get('total_playtime', 0) / 3600:.1f} hours")
        print(f"  Floors Climbed: {progress.get('floors_climbed', 0)}")
        print(f"  Architect Damage (yours): {progress.get('architect_damage', 0):,}")
        print(f"  Cards Discovered: {len(progress.get('discovered_cards', []))}")
        print(f"  Relics Discovered: {len(progress.get('discovered_relics', []))}")

    # Average run time
    run_times = [r.get("run_time", 0) for r in runs if r.get("run_time")]
    if run_times:
        avg_time = sum(run_times) / len(run_times)
        print(f"\n  Avg Run Time: {avg_time/60:.1f} min")
        win_times = [r.get("run_time", 0) for r in runs if r.get("win") and r.get("run_time")]
        if win_times:
            print(f"  Avg Win Time: {sum(win_times)/len(win_times)/60:.1f} min")


def analyze_characters(runs, progress):
    """Per-character breakdown."""
    print("\n" + "=" * 60)
    print("  CHARACTER STATISTICS")
    print("=" * 60)

    char_runs = defaultdict(list)
    for r in runs:
        players = r.get("players", [])
        if len(players) == 1:
            char = players[0].get("character", "Unknown")
            char_runs[char].append(r)

    for char in sorted(char_runs.keys()):
        char_list = char_runs[char]
        wins = sum(1 for r in char_list if r.get("win"))
        total = len(char_list)
        name = short_id(char)
        print(f"\n  {name}:")
        print(f"    Runs: {total}  Wins: {wins}  Win Rate: {wins/total*100:.1f}%" if total else "")

        # Ascension breakdown
        asc_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        for r in char_list:
            asc = r.get("ascension", 0)
            asc_stats[asc]["total"] += 1
            if r.get("win"):
                asc_stats[asc]["wins"] += 1
        if asc_stats:
            asc_str = "    Ascension: "
            for asc in sorted(asc_stats.keys()):
                s = asc_stats[asc]
                asc_str += f"A{asc}({s['wins']}/{s['total']}) "
            print(asc_str)

        # Common killers
        killers = Counter()
        for r in char_list:
            if not r.get("win") and not r.get("was_abandoned"):
                killer = r.get("killed_by_encounter", "Unknown")
                killers[short_id(killer)] += 1
        if killers:
            top_killers = killers.most_common(3)
            print(f"    Top Deaths: {', '.join(f'{k}({v})' for k, v in top_killers)}")

    if progress:
        print("\n  -- From Progress Save --")
        for cs in progress.get("character_stats", []):
            name = short_id(cs.get("id", ""))
            print(f"  {name}: Max Asc {cs.get('max_ascension', 0)} | "
                  f"Best Streak {cs.get('best_win_streak', 0)} | "
                  f"Playtime {cs.get('playtime', 0)/3600:.1f}h | "
                  f"Fastest Win {cs.get('fastest_win_time', 0)/60:.1f}min")


def analyze_cards(runs, progress):
    """Card pick rate and win rate analysis."""
    print("\n" + "=" * 60)
    print("  CARD ANALYSIS (from progress save)")
    print("=" * 60)

    if not progress:
        print("  No progress save found.")
        return

    card_stats = progress.get("card_stats", [])
    if not card_stats:
        return

    # Sort by times_picked descending
    by_picked = sorted(card_stats, key=lambda c: c.get("times_picked", 0), reverse=True)
    print("\n  Most Picked Cards:")
    print(f"  {'Card':<30} {'Picked':>7} {'Skipped':>8} {'Pick%':>6} {'WinRate':>8}")
    print("  " + "-" * 62)
    for c in by_picked[:20]:
        name = short_id(c.get("id", ""))
        picked = c.get("times_picked", 0)
        skipped = c.get("times_skipped", 0)
        won = c.get("times_won", 0)
        lost = c.get("times_lost", 0)
        offered = picked + skipped
        pick_rate = (picked / offered * 100) if offered > 0 else 0
        total_runs = won + lost
        win_rate = (won / total_runs * 100) if total_runs > 0 else 0
        if picked > 0:
            print(f"  {name:<30} {picked:>7} {skipped:>8} {pick_rate:>5.1f}% {win_rate:>6.1f}%")

    # Best win rate cards (min 3 runs)
    winnable = [c for c in card_stats if (c.get("times_won", 0) + c.get("times_lost", 0)) >= 3]
    by_winrate = sorted(winnable, key=lambda c: c.get("times_won", 0) / max(1, c.get("times_won", 0) + c.get("times_lost", 0)), reverse=True)
    print("\n  Highest Win Rate Cards (min 3 runs):")
    print(f"  {'Card':<30} {'Wins':>5} {'Losses':>7} {'WinRate':>8}")
    print("  " + "-" * 53)
    for c in by_winrate[:15]:
        name = short_id(c.get("id", ""))
        won = c.get("times_won", 0)
        lost = c.get("times_lost", 0)
        wr = won / (won + lost) * 100
        print(f"  {name:<30} {won:>5} {lost:>7} {wr:>6.1f}%")


def analyze_encounters(progress):
    """Encounter difficulty analysis."""
    print("\n" + "=" * 60)
    print("  ENCOUNTER ANALYSIS")
    print("=" * 60)

    if not progress:
        return

    encounters = progress.get("encounter_stats", [])
    if not encounters:
        return

    # Calculate overall win rate per encounter
    enc_data = []
    for enc in encounters:
        total_wins = sum(fs.get("wins", 0) for fs in enc.get("fight_stats", []))
        total_losses = sum(fs.get("losses", 0) for fs in enc.get("fight_stats", []))
        total = total_wins + total_losses
        if total > 0:
            enc_data.append({
                "name": short_id(enc["encounter_id"]),
                "wins": total_wins,
                "losses": total_losses,
                "total": total,
                "win_rate": total_wins / total * 100,
            })

    # Hardest encounters (lowest win rate, min 3 fights)
    hard = sorted([e for e in enc_data if e["total"] >= 3], key=lambda e: e["win_rate"])
    print("\n  Hardest Encounters (min 3 fights):")
    print(f"  {'Encounter':<40} {'W':>3} {'L':>3} {'WR':>6}")
    print("  " + "-" * 55)
    for e in hard[:15]:
        print(f"  {e['name']:<40} {e['wins']:>3} {e['losses']:>3} {e['win_rate']:>5.1f}%")


def analyze_run_detail(run):
    """Detailed analysis of a single run."""
    players = run.get("players", [])
    is_multi = len(players) > 1

    print("\n" + "=" * 60)
    chars = ", ".join(short_id(p.get("character", "?")) for p in players)
    result = "WIN" if run.get("win") else "LOSS"
    if run.get("was_abandoned"):
        result = "ABANDONED"
    print(f"  RUN: {chars} | {result} | A{run.get('ascension', 0)} | Seed: {run.get('seed', '?')}")
    print(f"  Time: {run.get('run_time', 0)/60:.1f}min | Started: {ts_to_str(run.get('start_time', 0))}")
    if not run.get("win"):
        print(f"  Killed by: {short_id(run.get('killed_by_encounter', 'Unknown'))}")
    print("=" * 60)

    # Floor-by-floor data
    floor_num = 0
    player_ids = {str(p.get("id", i)): short_id(p.get("character", f"P{i+1}")) for i, p in enumerate(players)}

    all_floors = []  # Collect for charting

    for act_idx, act in enumerate(run.get("map_point_history", [])):
        if not isinstance(act, list):
            continue
        act_names = run.get("acts", [])
        act_name = short_id(act_names[act_idx]) if act_idx < len(act_names) else f"Act {act_idx+1}"
        print(f"\n  --- {act_name} ---")

        for mp in act:
            floor_num += 1
            mp_type = mp.get("map_point_type", "?")
            rooms = mp.get("rooms", [])
            room_name = short_id(rooms[0].get("model_id", "?")) if rooms else "?"
            turns = rooms[0].get("turns_taken", 0) if rooms else 0

            stats = mp.get("player_stats", [])
            if is_multi:
                print(f"\n  F{floor_num:>2} [{mp_type:<8}] {room_name}" + (f" ({turns} turns)" if turns else ""))
                for ps in stats:
                    pid = str(ps.get("player_id", "?"))
                    pname = player_ids.get(pid, pid[-4:] if len(pid) > 4 else pid)
                    dmg = ps.get("damage_taken", 0)
                    hp = ps.get("current_hp", 0)
                    maxhp = ps.get("max_hp", 0)
                    gold = ps.get("current_gold", 0)
                    cards = [short_id(c["card"]["id"]) for c in ps.get("card_choices", []) if c.get("was_picked")]
                    relics = [short_id(c["choice"]) for c in ps.get("relic_choices", []) if c.get("was_picked")]
                    items = cards + relics
                    line = f"    {pname:<14} HP:{hp:>3}/{maxhp:<3} Dmg:{dmg:>3} Gold:{gold:>4}"
                    if items:
                        line += f"  +{', '.join(items)}"
                    print(line)
            else:
                ps = stats[0] if stats else {}
                dmg = ps.get("damage_taken", 0)
                hp = ps.get("current_hp", 0)
                maxhp = ps.get("max_hp", 0)
                gold = ps.get("current_gold", 0)
                cards = [short_id(c["card"]["id"]) for c in ps.get("card_choices", []) if c.get("was_picked")]
                relics = [short_id(c["choice"]) for c in ps.get("relic_choices", []) if c.get("was_picked")]
                items = cards + relics

                line = f"  F{floor_num:>2} [{mp_type:<8}] {room_name:<30} HP:{hp:>3}/{maxhp:<3} Dmg:{dmg:>3} Gold:{gold:>4}"
                if turns:
                    line += f" T:{turns}"
                if items:
                    line += f"  +{', '.join(items)}"
                print(line)

                all_floors.append({
                    "floor": floor_num,
                    "type": mp_type,
                    "hp": hp,
                    "max_hp": maxhp,
                    "damage": dmg,
                    "gold": gold,
                })

    # Final deck
    print("\n  Final Deck:")
    for p in players:
        pname = short_id(p.get("character", "?"))
        deck = p.get("deck", [])
        if is_multi:
            print(f"    {pname}:")
        for card in sorted(deck, key=lambda c: c.get("id", "")):
            name = short_id(card.get("id", "?"))
            upg = card.get("current_upgrade_level", 0)
            upg_str = f"+{upg}" if upg > 0 else ""
            prefix = "      " if is_multi else "    "
            print(f"{prefix}{name}{upg_str}")

    # Final relics
    print("\n  Final Relics:")
    for p in players:
        pname = short_id(p.get("character", "?"))
        relics = p.get("relics", [])
        if is_multi:
            print(f"    {pname}:")
        prefix = "      " if is_multi else "    "
        relic_names = [short_id(r.get("id", "?")) for r in relics]
        print(f"{prefix}{', '.join(relic_names)}")

    # ASCII chart for single player
    if all_floors and not is_multi:
        print_floor_charts(all_floors)


def print_floor_charts(floors):
    """Print ASCII charts for HP and damage per floor."""
    print("\n  HP Over Floors:")
    max_hp_val = max(f["max_hp"] for f in floors) if floors else 1
    bar_width = 40

    for f in floors:
        hp_pct = f["hp"] / max_hp_val if max_hp_val else 0
        bar_len = int(hp_pct * bar_width)
        bar = "#" * bar_len + "." * (bar_width - bar_len)
        print(f"  F{f['floor']:>2} |{bar}| {f['hp']:>3}/{f['max_hp']}")

    print("\n  Damage Taken Per Floor:")
    max_dmg = max((f["damage"] for f in floors), default=1) or 1
    for f in floors:
        if f["damage"] > 0:
            bar_len = int(f["damage"] / max_dmg * bar_width)
            bar = "X" * bar_len
            print(f"  F{f['floor']:>2} |{bar:<{bar_width}}| {f['damage']:>3} [{f['type']}]")


def analyze_multiplayer(runs):
    """Compare player performance across multiplayer runs."""
    multi_runs = [r for r in runs if len(r.get("players", [])) > 1]
    if not multi_runs:
        print("\n  No multiplayer runs found.")
        return

    print("\n" + "=" * 60)
    print(f"  MULTIPLAYER ANALYSIS ({len(multi_runs)} runs)")
    print("=" * 60)

    # Aggregate per-player stats across all multiplayer runs
    player_totals = defaultdict(lambda: {
        "damage_taken": 0, "gold_gained": 0, "gold_spent": 0,
        "hp_healed": 0, "max_hp_gained": 0, "floors": 0,
        "cards_gained": 0, "characters": Counter(), "runs": 0,
    })

    for run in multi_runs:
        player_chars = {}
        for p in run.get("players", []):
            pid = str(p.get("id", ""))
            player_chars[pid] = p.get("character", "?")
            player_totals[pid]["characters"][p.get("character", "?")] += 1
            player_totals[pid]["runs"] += 1

        for act in run.get("map_point_history", []):
            if not isinstance(act, list):
                continue
            for mp in act:
                for ps in mp.get("player_stats", []):
                    pid = str(ps.get("player_id", ""))
                    pt = player_totals[pid]
                    pt["damage_taken"] += ps.get("damage_taken", 0)
                    pt["gold_gained"] += ps.get("gold_gained", 0)
                    pt["gold_spent"] += ps.get("gold_spent", 0)
                    pt["hp_healed"] += ps.get("hp_healed", 0)
                    pt["max_hp_gained"] += ps.get("max_hp_gained", 0)
                    pt["cards_gained"] += len(ps.get("cards_gained", []))
                    pt["floors"] += 1

    print(f"\n  {'Player':<20} {'Runs':>5} {'DmgTaken':>9} {'GoldGained':>11} {'Healed':>7} {'Cards':>6}")
    print("  " + "-" * 62)
    for pid in sorted(player_totals.keys(), key=lambda p: player_totals[p]["damage_taken"], reverse=True):
        pt = player_totals[pid]
        most_played = pt["characters"].most_common(1)[0][0] if pt["characters"] else "?"
        name = f"{short_id(most_played)} ({pid[-4:]})"
        print(f"  {name:<20} {pt['runs']:>5} {pt['damage_taken']:>9} {pt['gold_gained']:>11} {pt['hp_healed']:>7} {pt['cards_gained']:>6}")


def watch_current_run(save_dir, interval=5):
    """Watch current_run.save for live updates."""
    path = os.path.join(save_dir, "profile1", "saves", "current_run.save")
    print(f"\n  Watching: {path}")
    print(f"  Polling every {interval}s. Press Ctrl+C to stop.\n")

    last_mtime = 0
    last_size = 0

    while True:
        try:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                size = os.path.getsize(path)
                if mtime != last_mtime or size != last_size:
                    last_mtime = mtime
                    last_size = size
                    try:
                        data = load_json(path)
                        print_live_status(data)
                    except (json.JSONDecodeError, IOError):
                        pass
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n  Stopped watching.")
            break


def print_live_status(data):
    """Print current run status."""
    ts = datetime.now().strftime("%H:%M:%S")
    players = data.get("players", [])
    chars = ", ".join(short_id(p.get("character", "?")) for p in players)

    # Count floors from map_point_history
    floor_count = 0
    last_hp = {}
    for act in data.get("map_point_history", []):
        if isinstance(act, list):
            for mp in act:
                floor_count += 1
                for ps in mp.get("player_stats", []):
                    pid = str(ps.get("player_id", ""))
                    last_hp[pid] = (ps.get("current_hp", 0), ps.get("max_hp", 0), ps.get("current_gold", 0))

    hp_str = " | ".join(f"HP:{hp}/{mhp} G:{g}" for hp, mhp, g in last_hp.values())
    print(f"  [{ts}] {chars} | Floor {floor_count} | {hp_str}")


def track_architect_damage(save_dir, log_dir):
    """Track architect damage from game logs over time."""
    print("\n" + "=" * 60)
    print("  ARCHITECT DAMAGE TRACKING")
    print("=" * 60)

    # Read from all log files
    entries = []
    for logfile in sorted(glob.glob(os.path.join(log_dir, "godot*.log"))):
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "architect damage =" in line.lower():
                    # Extract the number
                    parts = line.split("architect damage = ")
                    if len(parts) == 2:
                        try:
                            num = int(parts[1].strip())
                            # Get date from filename
                            fname = os.path.basename(logfile)
                            if "T" in fname:
                                datepart = fname.replace("godot", "").replace(".log", "")
                                entries.append((datepart, num))
                            else:
                                mtime = os.path.getmtime(logfile)
                                entries.append((ts_to_str(mtime), num))
                        except ValueError:
                            pass

    if not entries:
        print("  No architect damage data found in logs.")
        return

    print(f"\n  Global Architect Damage Over Time:")
    print(f"  {'Date':<25} {'Total Damage':>18} {'Delta':>15}")
    print("  " + "-" * 60)

    prev = None
    for date, dmg in entries:
        delta = ""
        if prev is not None:
            d = dmg - prev
            if d > 0:
                delta = f"+{d:,}"
        print(f"  {date:<25} {dmg:>18,} {delta:>15}")
        prev = dmg

    # Your contribution
    progress = load_progress(save_dir)
    if progress:
        your_dmg = progress.get("architect_damage", 0)
        global_dmg = entries[-1][1] if entries else 1
        print(f"\n  Your Contribution: {your_dmg:,} ({your_dmg/global_dmg*100:.6f}% of global)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Slay the Spire 2 Data Tracker")
    parser.add_argument("command", nargs="?", default="summary",
                        choices=["summary", "characters", "cards", "encounters",
                                 "runs", "run", "multiplayer", "watch", "architect", "all"],
                        help="What to analyze")
    parser.add_argument("--run", "-r", type=int, default=-1,
                        help="Run index to analyze in detail (0=oldest, -1=latest)")
    parser.add_argument("--watch-interval", type=int, default=5,
                        help="Polling interval for watch mode (seconds)")
    args = parser.parse_args()

    save_dir = find_save_dir()
    if not save_dir:
        print("ERROR: Could not find StS2 save directory in Steam userdata.")
        print(f"  Searched: {STEAM_USERDATA}")
        sys.exit(1)

    print(f"  Save directory: {save_dir}")

    runs = load_all_runs(save_dir)
    progress = load_progress(save_dir)
    print(f"  Loaded {len(runs)} runs, progress: {'yes' if progress else 'no'}")

    if args.command == "watch":
        watch_current_run(save_dir, args.watch_interval)
        return

    if args.command in ("summary", "all"):
        analyze_overall(runs, progress)

    if args.command in ("characters", "all"):
        analyze_characters(runs, progress)

    if args.command in ("cards", "all"):
        analyze_cards(runs, progress)

    if args.command in ("encounters", "all"):
        analyze_encounters(progress)

    if args.command in ("multiplayer", "all"):
        analyze_multiplayer(runs)

    if args.command in ("architect", "all"):
        track_architect_damage(save_dir, APPDATA_LOGS)

    if args.command == "runs":
        print("\n" + "=" * 60)
        print("  RUN HISTORY")
        print("=" * 60)
        print(f"\n  {'#':>3} {'Date':<18} {'Character':<16} {'A':>2} {'Result':<10} {'Time':>6} {'Seed':<12}")
        print("  " + "-" * 72)
        for i, r in enumerate(runs):
            players = r.get("players", [])
            chars = "/".join(short_id(p.get("character", "?"))[:8] for p in players)
            result = "WIN" if r.get("win") else "LOSS"
            if r.get("was_abandoned"):
                result = "ABANDONED"
            t = r.get("run_time", 0)
            print(f"  {i:>3} {ts_to_str(r.get('start_time', 0)):<18} {chars:<16} {r.get('ascension', 0):>2} {result:<10} {t//60:>3}m {r.get('seed', '?'):<12}")

    if args.command == "run":
        idx = args.run
        if not runs:
            print("  No runs found.")
            return
        run = runs[idx]
        analyze_run_detail(run)

    if args.command == "all":
        # Also show latest run detail
        if runs:
            print("\n  --- Latest Run Detail ---")
            analyze_run_detail(runs[-1])


if __name__ == "__main__":
    main()
