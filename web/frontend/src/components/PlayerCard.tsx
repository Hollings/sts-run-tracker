import React from "react";
import type { PlayerCombatStats } from "../utils/types";
import { formatGameId } from "../utils/format";

interface Props {
  playerId: string;
  stats: PlayerCombatStats;
  maxDamage?: number; // For scaling bars relative to other players
}

function StatBar({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-32 text-sts-text-dim">{label}</span>
      <span className="w-12 text-right font-mono font-semibold">{value}</span>
      <div className="flex-1 h-3 bg-sts-bg rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function PlayerCard({ playerId, stats, maxDamage }: Props) {
  const character = formatGameId(stats.character);
  const barMax = maxDamage || Math.max(stats.damage_dealt, stats.damage_taken, 1);

  // Sort damage_by_card by total_damage descending
  const cardDamageEntries = Object.entries(stats.damage_by_card || {}).sort(
    ([, a], [, b]) => b.total_damage - a.total_damage
  );

  // Sort damage_by_target descending
  const targetDamageEntries = Object.entries(stats.damage_by_target || {}).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <div className="bg-sts-card border border-sts-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-sts-gold">
          {character}
          <span className="text-sm text-sts-text-dim ml-2">
            (Player {playerId})
          </span>
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-sts-text-dim">Kills:</span>
          <span className="font-bold text-sts-red">{stats.kills}</span>
        </div>
      </div>

      <div className="space-y-1.5 mb-4">
        <StatBar
          label="Damage Dealt"
          value={stats.damage_dealt}
          max={barMax}
          color="bg-sts-red"
        />
        <StatBar
          label="Damage Taken"
          value={stats.damage_taken}
          max={barMax}
          color="bg-orange-500"
        />
        <StatBar
          label="Block Gained"
          value={stats.block_gained}
          max={barMax}
          color="bg-sts-blue"
        />
        <div className="flex items-center gap-3 text-sm">
          <span className="w-32 text-sts-text-dim">Cards Played</span>
          <span className="w-12 text-right font-mono font-semibold">
            {stats.cards_played}
          </span>
        </div>
      </div>

      {/* Top cards by damage */}
      {cardDamageEntries.length > 0 && (
        <div className="mt-3 pt-3 border-t border-sts-border">
          <h4 className="text-sm font-semibold text-sts-text-dim mb-2">
            Top Cards
          </h4>
          <div className="space-y-1">
            {cardDamageEntries.slice(0, 5).map(([cardId, dmg]) => (
              <div
                key={cardId}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-sts-gold-light">
                  {formatGameId(cardId)}
                </span>
                <span className="text-sts-text-dim font-mono">
                  {dmg.total_damage} dmg ({dmg.hits}x, max {dmg.max_hit})
                  {dmg.kills > 0 && (
                    <span className="text-sts-red ml-1">*</span>
                  )}
                </span>
              </div>
            ))}
            {cardDamageEntries.some(([, d]) => d.kills > 0) && (
              <p className="text-xs text-sts-text-dim mt-1">
                * = killing blow
              </p>
            )}
          </div>
        </div>
      )}

      {/* Damage by target */}
      {targetDamageEntries.length > 0 && (
        <div className="mt-3 pt-3 border-t border-sts-border">
          <h4 className="text-sm font-semibold text-sts-text-dim mb-2">
            Damage by Target
          </h4>
          <div className="space-y-1">
            {targetDamageEntries.map(([targetId, dmg]) => (
              <div
                key={targetId}
                className="flex items-center justify-between text-sm"
              >
                <span>{formatGameId(targetId)}</span>
                <span className="font-mono text-sts-red">{dmg}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
