// ---------------------------------------------------------------------------
// Tracker (live combat) types
// ---------------------------------------------------------------------------

export interface CardPlay {
  card: string;
  target?: string | null;
  turn: number;
}

export interface CardDamage {
  total_damage: number;
  hits: number;
  max_hit: number;
  kills: number;
}

export interface PlayerCombatStats {
  steam_id: string;
  character: string;
  damage_dealt: number;
  damage_taken: number;
  damage_blocked: number;
  block_gained: number;
  cards_played: number;
  kills: number;
  damage_per_turn: number[];
  block_per_turn: number[];
  cards_per_turn: number[];
  card_sequence: CardPlay[];
  damage_by_target: Record<string, number>;
  damage_by_card: Record<string, CardDamage>;
  damage_taken_per_turn: number[];
  damage_blocked_per_turn: number[];
  damage_taken_by_source: Record<string, DamageTakenSource>;
  hits_received: HitReceived[];
}

export interface DamageTakenSource {
  unblocked: number;
  blocked: number;
  hits: number;
  max_hit: number;
}

export interface HitReceived {
  source: string;
  unblocked: number;
  blocked: number;
  turn: number;
  was_killed: boolean;
}

export interface Combat {
  encounter: string;
  monsters: string[];
  floor: number;
  total_turns: number;
  result: string;
  players: Record<string, PlayerCombatStats>;
}

export interface TrackerData {
  mod_version: string;
  run_info: RunInfo;
  combats: Combat[];
}

// ---------------------------------------------------------------------------
// Run history types
// ---------------------------------------------------------------------------

export interface RunSummary {
  filename: string;
  seed: string;
  start_time: number;
  run_time: number;
  win: boolean;
  was_abandoned: boolean;
  ascension: number;
  characters: string[];
  killed_by: string;
  floor_count: number;
  game_mode: string;
}

export interface DeckCard {
  id: string;
  current_upgrade_level?: number;
  floor_added_to_deck?: number;
}

export interface RelicInfo {
  id: string;
  floor_added_to_deck?: number;
}

export interface PotionInfo {
  id: string;
  slot_index?: number;
}

export interface RunPlayer {
  id: number;
  character: string;
  deck: DeckCard[];
  relics: RelicInfo[];
  potions: PotionInfo[];
  max_potion_slot_count: number;
}

export interface RoomInfo {
  model_id: string;
  room_type: string;
  turns_taken: number;
  monster_ids?: string[];
}

export interface CardChoice {
  card?: { id: string; floor_added_to_deck?: number };
  was_picked: boolean;
}

export interface FloorPlayerStats {
  player_id: number;
  current_hp: number;
  max_hp: number;
  damage_taken: number;
  hp_healed: number;
  current_gold: number;
  gold_gained: number;
  gold_spent: number;
  gold_lost?: number;
  gold_stolen?: number;
  max_hp_gained?: number;
  max_hp_lost?: number;
  card_choices?: CardChoice[];
  relic_choices?: { choice: string; was_picked: boolean }[];
  potion_choices?: { choice: string; was_picked: boolean }[];
  cards_gained?: { id: string }[];
  cards_transformed?: { original_card: { id: string }; final_card: { id: string } }[];
  ancient_choice?: { TextKey: string; was_chosen: boolean }[];
  event_choices?: { title?: { key: string } }[];
}

export interface MapPoint {
  map_point_type: string;
  player_stats: FloorPlayerStats[];
  rooms: RoomInfo[];
}

export interface RunData {
  acts: string[];
  ascension: number;
  build_id: string;
  game_mode: string;
  killed_by_encounter: string;
  killed_by_event: string;
  seed: string;
  start_time: number;
  run_time: number;
  win: boolean;
  was_abandoned: boolean;
  platform_type: string;
  players: RunPlayer[];
  map_point_history: MapPoint[][];
  modifiers?: string[];
  schema_version?: number;
}

// ---------------------------------------------------------------------------
// Progress (lifetime stats) types
// ---------------------------------------------------------------------------

export interface CharacterStat {
  id: string;
  total_wins: number;
  total_losses: number;
  best_win_streak: number;
  current_streak: number;
  fastest_win_time: number;
  max_ascension: number;
  playtime: number;
  preferred_ascension?: number;
}

export interface CardStat {
  id: string;
  times_picked: number;
  times_skipped: number;
  times_won: number;
  times_lost: number;
}

export interface FightStat {
  character: string;
  wins: number;
  losses: number;
}

export interface EncounterStat {
  encounter_id: string;
  fight_stats: FightStat[];
}

export interface ProgressData {
  character_stats: CharacterStat[];
  card_stats: CardStat[];
  encounter_stats: EncounterStat[];
  total_playtime: number;
  floors_climbed: number;
  architect_damage: number;
}

// ---------------------------------------------------------------------------
// Merged live data (from merge.py: tracker + save combined)
// ---------------------------------------------------------------------------

export interface RunInfoPlayer {
  steam_id: string;
  character: string;
}

export interface RunInfo {
  seed?: string;
  ascension?: number;
  players?: RunInfoPlayer[];
  [key: string]: unknown;
}

export interface FloorPlayer {
  player_id: string;
  hp: number;
  max_hp: number;
  damage_taken: number;
  hp_healed: number;
  gold: number;
  gold_gained: number;
  gold_spent: number;
  cards_picked: string[];
  cards_skipped: string[];
  relics_picked: string[];
  potions_picked: string[];
  event_choices: string[];
}

export interface Floor {
  floor: number;
  act: number;
  type: string;
  room_id: string;
  room_type: string;
  turns_taken: number;
  monsters: string[];
  players: FloorPlayer[];
  combat?: Combat;
}

export interface BestHit {
  card: string;
  damage: number;
  encounter: string;
}

export interface CardDamageAgg {
  total_damage: number;
  hits: number;
  max_hit: number;
  kills: number;
}

export interface PlayerRunTotals {
  steam_id: string;
  character: string;
  damage_dealt: number;
  damage_taken: number;
  damage_blocked: number;
  block_gained: number;
  cards_played: number;
  kills: number;
  combats: number;
  best_hit: BestHit;
  damage_by_card: Record<string, CardDamageAgg>;
}

export interface RunTotalsData {
  total_combats: number;
  wins: number;
  losses: number;
  players: Record<string, PlayerRunTotals>;
}

export interface MergedLiveData {
  run_info: RunInfo;
  floors: Floor[];
  combats: Combat[];
  run_totals: RunTotalsData;
}

// ---------------------------------------------------------------------------
// WebSocket message
// ---------------------------------------------------------------------------

export interface WSMessage {
  type: string;
  data?: MergedLiveData | null;
}
