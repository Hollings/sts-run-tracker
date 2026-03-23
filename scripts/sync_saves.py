"""Sync unmodded save data to modded profile so modded play has full progress.

The game keeps modded/unmodded saves separate and rebuilds progress from run
history on launch. This script copies run history and progress.save from the
unmodded profile to the modded profile.

Run this BEFORE launching the game with mods enabled.
"""

import json
import os
import shutil
import sys


def find_save_base():
    """Find the game's primary save directory in %APPDATA%."""
    appdata = os.environ.get("APPDATA", "")
    steam_dir = os.path.join(appdata, "SlayTheSpire2", "steam")
    if not os.path.isdir(steam_dir):
        print(f"ERROR: Save directory not found: {steam_dir}")
        sys.exit(1)
    # Find the steam ID directory
    candidates = [
        os.path.join(steam_dir, d)
        for d in os.listdir(steam_dir)
        if os.path.isdir(os.path.join(steam_dir, d))
    ]
    if not candidates:
        print(f"ERROR: No Steam ID directories found in {steam_dir}")
        sys.exit(1)
    if len(candidates) > 1:
        # Pick most recently modified
        candidates.sort(key=os.path.getmtime, reverse=True)
        print(f"Multiple Steam IDs found, using: {os.path.basename(candidates[0])}")
    return candidates[0]


def get_playtime(progress_path):
    """Read total_playtime from a progress.save file."""
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("total_playtime", 0)
    except (IOError, json.JSONDecodeError):
        return 0


def get_stats(progress_path):
    """Read summary stats from a progress.save file."""
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        chars = data.get("character_stats", [])
        total_w = sum(c.get("total_wins", 0) for c in chars)
        total_l = sum(c.get("total_losses", 0) for c in chars)
        playtime = data.get("total_playtime", 0)
        return total_w, total_l, playtime
    except (IOError, json.JSONDecodeError):
        return 0, 0, 0


def format_time(seconds):
    """Format seconds into h:mm:ss."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"


def count_runs(history_dir):
    """Count .run files in a history directory."""
    if not os.path.isdir(history_dir):
        return 0
    return len([f for f in os.listdir(history_dir) if f.endswith(".run")])


def main():
    force = "--force" in sys.argv or "-f" in sys.argv
    base = find_save_base()
    unmodded_saves = os.path.join(base, "profile1", "saves")
    modded_saves = os.path.join(base, "modded", "profile1", "saves")

    unmodded_progress = os.path.join(unmodded_saves, "progress.save")
    modded_progress = os.path.join(modded_saves, "progress.save")
    unmodded_history = os.path.join(unmodded_saves, "history")
    modded_history = os.path.join(modded_saves, "history")

    if not os.path.exists(unmodded_progress):
        print("ERROR: No unmodded progress.save found. Nothing to sync.")
        sys.exit(1)

    # Show unmodded stats
    uw, ul, upt = get_stats(unmodded_progress)
    u_runs = count_runs(unmodded_history)
    print(f"Unmodded profile: {uw}W {ul}L, {format_time(upt)} playtime, {u_runs} runs")

    # Check modded profile
    if os.path.exists(modded_progress):
        mw, ml, mpt = get_stats(modded_progress)
        m_runs = count_runs(modded_history)
        print(f"Modded profile:   {mw}W {ml}L, {format_time(mpt)} playtime, {m_runs} runs")

        if mpt > 300 and not force:  # more than 5 minutes
            print()
            print(f"WARNING: Modded profile has {format_time(mpt)} of play time.")
            print("Syncing will overwrite modded progress with unmodded data.")
            print("Modded-only run history will be preserved (not deleted).")
            response = input("Continue? [y/N] ").strip().lower()
            if response != "y":
                print("Aborted.")
                sys.exit(0)
    else:
        print("Modded profile: not yet created")

    # Create modded saves dir if needed
    os.makedirs(modded_saves, exist_ok=True)
    os.makedirs(modded_history, exist_ok=True)

    # Copy progress.save
    shutil.copy2(unmodded_progress, modded_progress)
    print(f"Copied progress.save ({os.path.getsize(modded_progress):,} bytes)")

    # Copy run history (don't overwrite existing modded-only runs)
    copied = 0
    skipped = 0
    if os.path.isdir(unmodded_history):
        for filename in os.listdir(unmodded_history):
            if not filename.endswith(".run"):
                continue
            src = os.path.join(unmodded_history, filename)
            dst = os.path.join(modded_history, filename)
            if os.path.exists(dst):
                skipped += 1
            else:
                shutil.copy2(src, dst)
                copied += 1

    total_modded_runs = count_runs(modded_history)
    print(f"Run history: {copied} copied, {skipped} already existed, {total_modded_runs} total")
    print()
    print("Sync complete. Launch the game with mods enabled.")


if __name__ == "__main__":
    main()
