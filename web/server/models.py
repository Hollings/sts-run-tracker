"""Pydantic models for StS2 Tracker data."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Mod tracker JSON (live combat data)
# ---------------------------------------------------------------------------

class CardPlay(BaseModel):
    card: str
    target: Optional[str] = None
    turn: int


class CardDamage(BaseModel):
    total_damage: int
    hits: int
    max_hit: int
    kills: int = 0


class PlayerCombatStats(BaseModel):
    steam_id: str
    character: str
    damage_dealt: int = 0
    damage_taken: int = 0
    damage_blocked: int = 0
    block_gained: int = 0
    cards_played: int = 0
    kills: int = 0
    damage_per_turn: list[int] = []
    block_per_turn: list[int] = []
    cards_per_turn: list[int] = []
    card_sequence: list[CardPlay] = []
    damage_by_target: dict[str, int] = {}
    damage_by_card: dict[str, CardDamage] = {}


class Combat(BaseModel):
    encounter: str
    monsters: list[str] = []
    floor_index: int = 0
    total_turns: int = 0
    result: str = "unknown"
    players: dict[str, PlayerCombatStats] = {}


class TrackerData(BaseModel):
    mod_version: str = "0.0.0"
    seed: str = ""
    start_time: int = 0
    combats: list[Combat] = []


# ---------------------------------------------------------------------------
# Game save files (historical run data)
# ---------------------------------------------------------------------------

class DeckCard(BaseModel):
    id: str
    current_upgrade_level: int = 0
    floor_added_to_deck: int = 0


class Relic(BaseModel):
    id: str
    floor_added_to_deck: int = 0


class Potion(BaseModel):
    id: str
    slot_index: int = 0


class RunPlayer(BaseModel):
    id: int = 0
    character: str = ""
    deck: list[DeckCard] = []
    relics: list[Relic] = []
    potions: list[Potion] = []
    max_potion_slot_count: int = 3


class CardChoice(BaseModel):
    card: Optional[dict] = None
    was_picked: bool = False


class RelicChoice(BaseModel):
    choice: str = ""
    was_picked: bool = False


class PotionChoice(BaseModel):
    choice: str = ""
    was_picked: bool = False


class RoomInfo(BaseModel):
    model_id: str = ""
    room_type: str = ""
    turns_taken: int = 0
    monster_ids: list[str] = []


class FloorPlayerStats(BaseModel):
    player_id: int = 0
    current_hp: int = 0
    max_hp: int = 0
    damage_taken: int = 0
    hp_healed: int = 0
    current_gold: int = 0
    gold_gained: int = 0
    gold_spent: int = 0
    gold_lost: int = 0
    gold_stolen: int = 0
    max_hp_gained: int = 0
    max_hp_lost: int = 0
    card_choices: list[CardChoice] = []
    relic_choices: list[RelicChoice] = []
    potion_choices: list[PotionChoice] = []
    cards_gained: list[dict] = []
    cards_transformed: list[dict] = []
    ancient_choice: list[dict] = []
    event_choices: list[dict] = []


class MapPoint(BaseModel):
    map_point_type: str = ""
    player_stats: list[FloorPlayerStats] = []
    rooms: list[RoomInfo] = []


class RunData(BaseModel):
    """Full run save file."""
    acts: list[str] = []
    ascension: int = 0
    build_id: str = ""
    game_mode: str = "standard"
    killed_by_encounter: str = "NONE.NONE"
    killed_by_event: str = "NONE.NONE"
    seed: str = ""
    start_time: int = 0
    run_time: int = 0
    win: bool = False
    was_abandoned: bool = False
    platform_type: str = "steam"
    players: list[RunPlayer] = []
    map_point_history: list[list[MapPoint]] = []
    modifiers: list[str] = []
    schema_version: int = 0


class RunSummary(BaseModel):
    """Lightweight summary for run list."""
    filename: str
    seed: str = ""
    start_time: int = 0
    run_time: int = 0
    win: bool = False
    was_abandoned: bool = False
    ascension: int = 0
    characters: list[str] = []
    killed_by: str = ""
    floor_count: int = 0
    game_mode: str = "standard"


# ---------------------------------------------------------------------------
# Progress save (lifetime stats)
# ---------------------------------------------------------------------------

class CharacterStat(BaseModel):
    id: str
    total_wins: int = 0
    total_losses: int = 0
    best_win_streak: int = 0
    current_streak: int = 0
    fastest_win_time: int = 0
    max_ascension: int = 0
    playtime: int = 0
    preferred_ascension: int = 0


class CardStat(BaseModel):
    id: str
    times_picked: int = 0
    times_skipped: int = 0
    times_won: int = 0
    times_lost: int = 0


class FightStat(BaseModel):
    character: str
    wins: int = 0
    losses: int = 0


class EncounterStat(BaseModel):
    encounter_id: str
    fight_stats: list[FightStat] = []


class ProgressData(BaseModel):
    character_stats: list[CharacterStat] = []
    card_stats: list[CardStat] = []
    encounter_stats: list[EncounterStat] = []
    total_playtime: int = 0
    floors_climbed: int = 0
    architect_damage: int = 0


# ---------------------------------------------------------------------------
# WebSocket message
# ---------------------------------------------------------------------------

class WSMessage(BaseModel):
    type: str
    data: Optional[dict] = None
