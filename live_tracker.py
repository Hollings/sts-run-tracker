"""
StS2 Live Tracker - watches mod output + game logs in real time.
Run this in a terminal while playing. It tails the tracker JSON and game logs
to show combat stats as they happen.

Usage: py live_tracker.py
"""

import json
import os
import sys
import time
import glob
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TRACKER_DIR = os.path.join(os.environ.get("APPDATA", ""), "SlayTheSpire2", "tracker")
LOG_DIR = os.path.join(os.environ.get("APPDATA", ""), "SlayTheSpire2", "logs")

CLEAR = "\033[2J\033[H"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
WHITE = "\033[97m"


def short_id(full_id):
    if not full_id:
        return "?"
    if "." in full_id:
        full_id = full_id.split(".", 1)[1]
    return full_id.replace("_", " ").title()


def bar(value, max_val, width=20, char="#", empty="."):
    if max_val <= 0:
        return empty * width
    filled = int(value / max_val * width)
    filled = min(filled, width)
    return char * filled + empty * (width - filled)


def format_card_sequence(seq, limit=8):
    if not seq:
        return ""
    cards = [short_id(c.get("card", "")) for c in seq[-limit:]]
    prefix = "... " if len(seq) > limit else ""
    return prefix + " -> ".join(cards)


def render_combat(combat, index):
    enc = short_id(combat.get("encounter", ""))
    result = combat.get("result", "?")
    turns = combat.get("total_turns", 0)
    result_color = GREEN if result == "win" else RED

    lines = []
    lines.append(f"  {BOLD}{CYAN}Combat {index}{RESET}: {enc} "
                 f"[{result_color}{result.upper()}{RESET}] "
                 f"{DIM}({turns} turns){RESET}")

    players = combat.get("players", {})
    if not players:
        return lines

    # Find max values for bars
    max_dealt = max((p.get("damage_dealt", 0) for p in players.values()), default=1) or 1
    max_taken = max((p.get("damage_taken", 0) for p in players.values()), default=1) or 1

    for pid, stats in players.items():
        char_name = short_id(stats.get("character", ""))
        dealt = stats.get("damage_dealt", 0)
        taken = stats.get("damage_taken", 0)
        blocked = stats.get("damage_blocked", 0)
        block = stats.get("block_gained", 0)
        cards = stats.get("cards_played", 0)
        kills = stats.get("kills", 0)

        lines.append(f"    {YELLOW}{char_name}{RESET} {DIM}({pid[-4:]}){RESET}")
        lines.append(f"      Dealt: {GREEN}{dealt:>4}{RESET} |{GREEN}{bar(dealt, max_dealt)}{RESET}|  "
                     f"Taken: {RED}{taken:>4}{RESET} |{RED}{bar(taken, max_taken)}{RESET}|")
        lines.append(f"      Block: {CYAN}{block:>4}{RESET}  Blocked: {CYAN}{blocked:>4}{RESET}  "
                     f"Cards: {WHITE}{cards:>3}{RESET}  Kills: {MAGENTA}{kills}{RESET}")

        # Per-turn damage sparkline
        dpt = stats.get("damage_per_turn", [])
        if dpt:
            spark_max = max(dpt) or 1
            spark = ""
            for v in dpt:
                height = int(v / spark_max * 4)
                spark += [" ", ".", ":", "|", "#"][height]
            lines.append(f"      Dmg/turn: [{spark}] peak={max(dpt)}")

        # Recent cards
        seq = stats.get("card_sequence", [])
        if seq:
            lines.append(f"      Last cards: {DIM}{format_card_sequence(seq)}{RESET}")

        # Damage by target
        by_target = stats.get("damage_by_target", {})
        if by_target:
            targets = ", ".join(f"{short_id(t)}={d}" for t, d in
                              sorted(by_target.items(), key=lambda x: -x[1])[:3])
            lines.append(f"      Targets: {DIM}{targets}{RESET}")

    return lines


def render_run_summary(data):
    combats = data.get("combats", [])
    if not combats:
        return []

    lines = []
    # Aggregate across all combats
    totals = defaultdict(lambda: {"dealt": 0, "taken": 0, "block": 0, "cards": 0, "kills": 0, "char": ""})
    for c in combats:
        for pid, stats in c.get("players", {}).items():
            t = totals[pid]
            t["dealt"] += stats.get("damage_dealt", 0)
            t["taken"] += stats.get("damage_taken", 0)
            t["block"] += stats.get("block_gained", 0)
            t["cards"] += stats.get("cards_played", 0)
            t["kills"] += stats.get("kills", 0)
            t["char"] = stats.get("character", t["char"])

    wins = sum(1 for c in combats if c.get("result") == "win")
    losses = len(combats) - wins

    lines.append(f"  {BOLD}Run Totals{RESET}: {len(combats)} combats "
                 f"({GREEN}{wins}W{RESET}/{RED}{losses}L{RESET})")

    for pid, t in totals.items():
        char_name = short_id(t["char"])
        lines.append(f"    {YELLOW}{char_name}{RESET}: "
                     f"Dealt={GREEN}{t['dealt']}{RESET} "
                     f"Taken={RED}{t['taken']}{RESET} "
                     f"Block={CYAN}{t['block']}{RESET} "
                     f"Cards={WHITE}{t['cards']}{RESET} "
                     f"Kills={MAGENTA}{t['kills']}{RESET}")

    return lines


def get_latest_tracker_file():
    if not os.path.isdir(TRACKER_DIR):
        return None
    files = glob.glob(os.path.join(TRACKER_DIR, "*.json"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def tail_log_lines(n=15):
    """Get the last n [StS2Tracker] lines from the latest game log."""
    log_file = os.path.join(LOG_DIR, "godot.log")
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tracker_lines = [l.strip() for l in lines if "[StS2Tracker]" in l]
        return tracker_lines[-n:]
    except:
        return []


def main():
    print(f"{BOLD}StS2 Live Tracker{RESET}")
    print(f"Watching: {TRACKER_DIR}")
    print(f"Log dir:  {LOG_DIR}")
    print(f"Press Ctrl+C to stop.\n")

    last_mtime = 0
    last_data = None

    while True:
        try:
            tracker_file = get_latest_tracker_file()
            needs_redraw = False

            if tracker_file:
                mtime = os.path.getmtime(tracker_file)
                if mtime != last_mtime:
                    last_mtime = mtime
                    try:
                        with open(tracker_file, "r", encoding="utf-8") as f:
                            last_data = json.load(f)
                        needs_redraw = True
                    except (json.JSONDecodeError, IOError):
                        pass

            if needs_redraw and last_data:
                output = []
                output.append(CLEAR)
                output.append(f"{BOLD}=== StS2 Live Tracker ==={RESET}  "
                              f"{DIM}{datetime.now().strftime('%H:%M:%S')}{RESET}")
                output.append(f"Seed: {last_data.get('seed', '?')}  "
                              f"File: {os.path.basename(tracker_file)}")
                output.append("")

                combats = last_data.get("combats", [])

                # Show run summary
                summary = render_run_summary(last_data)
                output.extend(summary)
                output.append("")

                # Show last 3 combats in detail
                start = max(0, len(combats) - 3)
                for i, combat in enumerate(combats[start:], start + 1):
                    combat_lines = render_combat(combat, i)
                    output.extend(combat_lines)
                    output.append("")

                # Show recent mod log lines
                log_lines = tail_log_lines(8)
                if log_lines:
                    output.append(f"{DIM}--- Mod Log ---{RESET}")
                    for line in log_lines:
                        # Strip the [StS2Tracker] prefix for cleaner display
                        cleaned = line.replace("[StS2Tracker] ", "")
                        output.append(f"  {DIM}{cleaned}{RESET}")

                print("\n".join(output))

            elif not last_data:
                # No data yet - show waiting state with log tail
                log_lines = tail_log_lines(5)
                ts = datetime.now().strftime('%H:%M:%S')
                status = "Waiting for tracker data..."
                if log_lines:
                    status = "Mod loaded, waiting for first combat..."
                print(f"\r{DIM}[{ts}] {status}{RESET}", end="", flush=True)

            time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n{RESET}Stopped.")
            break
        except Exception as ex:
            print(f"Error: {ex}")
            time.sleep(2)


if __name__ == "__main__":
    main()
