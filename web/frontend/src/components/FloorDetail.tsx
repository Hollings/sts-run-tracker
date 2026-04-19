import React from "react";
import type { Floor, FloorPlayer, PlayerCombatStats } from "../utils/types";
import {
  formatGameId,
  FLOOR_TYPE_LABELS,
  floorTypeBgColor,
  floorTypeTextColor,
  floorTypeBorderColor,
} from "../utils/format";
import DamageChart from "./DamageChart";

export function StatRow({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-xs text-sts-text">{label}</span>
      <span className={`text-lg font-bold ${color}`}>{value}</span>
    </div>
  );
}

export function FloorDetailView({
  floor,
  isLive,
  onGoLive,
}: {
  floor: Floor;
  isLive: boolean;
  onGoLive?: () => void;
}) {
  const combat = floor.combat;
  const typeLabel = FLOOR_TYPE_LABELS[floor.type] || floor.type;
  const playerEntries = combat ? Object.entries(combat.players) : [];

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Floor header */}
      <div
        className={`bg-sts-surface border rounded-lg p-4 shrink-0 ${
          isLive && combat?.result === "in_progress"
            ? "border-yellow-500/80 ring-1 ring-yellow-500/30"
            : "border-sts-border"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center justify-center w-10 h-10 rounded-lg text-sm font-bold ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(floor.type)} border ${floorTypeBorderColor(floor.type)}`}
            >
              {floor.floor}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-sts-gold">
                  {floor.room_id || "Unknown"}
                </span>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(floor.type)}`}
                >
                  {typeLabel}
                </span>
                {isLive && combat?.result === "in_progress" && (
                  <span className="px-2 py-0.5 text-xs font-bold uppercase tracking-wider bg-yellow-500/20 text-yellow-400 rounded animate-pulse">
                    Live
                  </span>
                )}
              </div>
              {floor.monsters.length > 0 && (
                <p className="text-sm text-sts-text">
                  vs {floor.monsters.join(", ")}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {combat && (
              <span
                className={`text-lg font-bold ${
                  combat.result === "in_progress"
                    ? "text-yellow-400"
                    : combat.result === "win"
                      ? "text-sts-green"
                      : "text-sts-red"
                }`}
              >
                {combat.result === "in_progress"
                  ? "FIGHTING"
                  : combat.result === "win"
                    ? "WIN"
                    : "LOSS"}
              </span>
            )}
            {!isLive && onGoLive && (
              <button
                onClick={onGoLive}
                className="px-3 py-1.5 text-xs font-semibold bg-yellow-500/20 text-yellow-400 rounded hover:bg-yellow-500/30 border border-yellow-500/30"
              >
                Go Live
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Combat content */}
      {combat && playerEntries.length > 0 ? (
        <div className="flex-1 min-h-0 flex flex-col gap-4 overflow-y-auto">
          <div
            className={`grid gap-3 shrink-0 ${playerEntries.length > 2 ? "grid-cols-3" : playerEntries.length > 1 ? "grid-cols-2" : "grid-cols-1"}`}
          >
            {playerEntries.map(([pid, stats]) => (
              <CombatPlayerCard key={pid} playerId={pid} stats={stats} />
            ))}
          </div>

          {playerEntries.some(([, s]) => s.damage_per_turn.length > 0) && (
            <div className="bg-sts-surface border border-sts-border rounded-lg p-4 shrink-0">
              <h4 className="text-sm font-semibold text-sts-text mb-2">
                Per-Turn Breakdown
              </h4>
              <DamageChart players={combat.players} />
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 bg-sts-surface border border-sts-border rounded-lg p-4">
          <div
            className={`grid gap-3 ${floor.players.length > 1 ? "md:grid-cols-2" : "grid-cols-1"}`}
          >
            {floor.players.map((p, i) => (
              <NonCombatPlayerCard key={i} player={p} floorType={floor.type} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CombatPlayerCard({
  playerId,
  stats,
}: {
  playerId: string;
  stats: PlayerCombatStats;
}) {
  const cardEntries = Object.entries(stats.damage_by_card || {})
    .sort(([, a], [, b]) => b.total_damage - a.total_damage)
    .slice(0, 4);

  return (
    <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
      <h4 className="text-sm font-semibold text-sts-gold mb-3">
        {formatGameId(stats.character)}
      </h4>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-3">
        <StatRow label="Damage" value={stats.damage_dealt} color="text-sts-red" />
        <StatRow label="Taken" value={stats.damage_taken} color="text-orange-400" />
        <StatRow label="Block" value={stats.block_gained} color="text-sts-blue" />
        <StatRow label="Cards" value={stats.cards_played} color="text-sts-text" />
      </div>
      {cardEntries.length > 0 && (
        <div className="border-t border-sts-border/50 pt-2 space-y-1">
          {cardEntries.map(([cardId, dmg]) => (
            <div key={cardId} className="flex justify-between text-xs">
              <span className="text-sts-gold-light truncate mr-2">
                {formatGameId(cardId)}
              </span>
              <span className="text-sts-text font-mono whitespace-nowrap">
                {dmg.total_damage}
                <span className="text-sts-text/50 ml-1">({dmg.hits}x)</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NonCombatPlayerCard({
  player,
  floorType,
}: {
  player: FloorPlayer;
  floorType: string;
}) {
  const hpPct =
    player.max_hp > 0 ? (player.hp / player.max_hp) * 100 : 0;
  const hpColor =
    hpPct > 60 ? "bg-sts-green" : hpPct > 30 ? "bg-yellow-500" : "bg-sts-red";

  const restChoices = player.rest_site_choices ?? [];
  const upgradedCards = player.upgraded_cards ?? [];
  const eventChoices = player.event_choices ?? [];
  const hasAnyDetail =
    restChoices.length > 0 ||
    upgradedCards.length > 0 ||
    eventChoices.some((e) => e) ||
    player.cards_picked.length > 0 ||
    player.cards_skipped.length > 0 ||
    player.relics_picked.length > 0 ||
    player.potions_picked.length > 0 ||
    player.gold_spent > 0 ||
    player.gold_gained > 0 ||
    player.damage_taken > 0 ||
    player.hp_healed > 0;

  return (
    <div className="bg-sts-card rounded-lg p-3 space-y-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-sts-text">Player {player.player_id}</span>
        <span>
          <span className="text-sts-red font-semibold">{player.hp}</span>
          <span className="text-sts-text">/{player.max_hp}</span>
          <span className="text-yellow-400 ml-2">{player.gold}g</span>
        </span>
      </div>
      <div className="h-2 bg-sts-surface rounded-full overflow-hidden">
        <div
          className={`h-full ${hpColor} rounded-full`}
          style={{ width: `${hpPct}%` }}
        />
      </div>

      {(player.damage_taken > 0 || player.hp_healed > 0) && (
        <div className="flex gap-3 text-xs">
          {player.damage_taken > 0 && (
            <span className="text-orange-400">-{player.damage_taken} HP</span>
          )}
          {player.hp_healed > 0 && (
            <span className="text-sts-green">+{player.hp_healed} healed</span>
          )}
        </div>
      )}

      {(player.gold_gained > 0 || player.gold_spent > 0) && (
        <div className="flex gap-3 text-xs">
          {player.gold_gained > 0 && (
            <span className="text-yellow-400">+{player.gold_gained}g gained</span>
          )}
          {player.gold_spent > 0 && (
            <span className="text-orange-400">-{player.gold_spent}g spent</span>
          )}
        </div>
      )}

      {restChoices.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Rest action: </span>
          {restChoices.map((c, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-green-900/30 text-green-400 rounded mr-1 font-medium"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {upgradedCards.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Upgraded: </span>
          {upgradedCards.map((c, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-sts-gold/10 text-sts-gold-light rounded mr-1 font-medium"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {eventChoices.length > 0 && eventChoices.some((e) => e) && (
        <div className="text-xs">
          <span className="text-sts-text">Chose: </span>
          {eventChoices
            .filter((e) => e)
            .map((e, i) => (
              <span
                key={i}
                className="inline-block px-1.5 py-0.5 bg-blue-900/20 text-blue-300 rounded mr-1 font-medium"
              >
                {e}
              </span>
            ))}
        </div>
      )}

      {player.cards_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Picked: </span>
          {player.cards_picked.map((c, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-green-900/30 text-sts-green rounded mr-1 mb-0.5 font-medium"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {player.cards_skipped.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Available: </span>
          {player.cards_skipped.map((c, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-sts-surface text-sts-text rounded mr-1 mb-0.5"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {player.relics_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Relics: </span>
          {player.relics_picked.map((r, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-amber-900/30 text-sts-amber rounded mr-1 mb-0.5 font-medium"
            >
              {r}
            </span>
          ))}
        </div>
      )}

      {player.potions_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Potions: </span>
          {player.potions_picked.map((p, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-blue-900/30 text-sts-blue rounded mr-1 mb-0.5 font-medium"
            >
              {p}
            </span>
          ))}
        </div>
      )}

      {!hasAnyDetail && (
        <div className="text-xs text-sts-text">No changes this floor</div>
      )}
    </div>
  );
}
