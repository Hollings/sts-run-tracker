import React from "react";
import type { Combat } from "../utils/types";
import { formatGameId } from "../utils/format";
import PlayerCard from "./PlayerCard";
import DamageChart from "./DamageChart";
import CardStats from "./CardStats";

interface Props {
  combat: Combat;
  index: number;
  expanded?: boolean;
  onToggle?: () => void;
}

export default function CombatDetail({
  combat,
  index,
  expanded = false,
  onToggle,
}: Props) {
  const isWin = combat.result === "win";
  const isInProgress = combat.result === "in_progress";
  const playerEntries = Object.entries(combat.players);

  return (
    <div className="bg-sts-surface border border-sts-border rounded-lg overflow-hidden">
      {/* Header - always visible, clickable */}
      <button
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-sts-card/50 text-left"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              isInProgress ? "bg-yellow-500" : isWin ? "bg-sts-green" : "bg-sts-red"
            }`}
          />
          <span className="font-semibold text-sts-gold">
            Floor {combat.floor}
          </span>
          <span className="text-sts-text">
            {formatGameId(combat.encounter)}
          </span>
          <span className="text-sts-text text-sm">
            vs {combat.monsters.map(formatGameId).join(", ")}
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-sts-text">
            {combat.total_turns} turn{combat.total_turns !== 1 ? "s" : ""}
          </span>
          <span className={isInProgress ? "text-yellow-400 font-bold" : isWin ? "text-sts-green font-bold" : "text-sts-red font-bold"}>
            {isInProgress ? "IN PROGRESS" : isWin ? "WIN" : "LOSS"}
          </span>
          <span className="text-sts-text">
            {expanded ? "[-]" : "[+]"}
          </span>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-6">
          {/* Player cards */}
          <div className={`grid gap-4 ${playerEntries.length > 1 ? "md:grid-cols-2" : "grid-cols-1"}`}>
            {playerEntries.map(([pid, stats]) => (
              <PlayerCard
                key={pid}
                playerId={pid}
                stats={stats}
                maxDamage={Math.max(
                  ...playerEntries.map(([, s]) =>
                    Math.max(s.damage_dealt, s.damage_taken, 1)
                  )
                )}
              />
            ))}
          </div>

          {/* Combined per-turn chart */}
          {playerEntries.some(([, s]) => s.damage_per_turn.length > 0) && (
            <div className="bg-sts-card rounded-lg p-4">
              <h5 className="text-sm font-semibold text-sts-text mb-2">
                Per-Turn Breakdown
              </h5>
              <DamageChart players={combat.players} />
            </div>
          )}

          {/* Per-player detailed breakdowns */}
          {playerEntries.map(([pid, stats]) => (
            <div key={`detail-${pid}`} className="space-y-4">
              <h4 className="text-md font-semibold text-sts-gold border-b border-sts-border pb-1">
                {formatGameId(stats.character)} - Detailed Breakdown
              </h4>

              {/* Card damage table */}
              {stats.damage_by_card &&
                Object.keys(stats.damage_by_card).length > 0 && (
                  <div className="bg-sts-card rounded-lg p-4">
                    <h5 className="text-sm font-semibold text-sts-text mb-2">
                      Damage by Card
                    </h5>
                    <CardStats damageByCard={stats.damage_by_card} />
                  </div>
                )}

              {/* Card sequence */}
              {stats.card_sequence.length > 0 && (
                <div className="bg-sts-card rounded-lg p-4">
                  <h5 className="text-sm font-semibold text-sts-text mb-3">
                    Card Sequence
                  </h5>
                  <div className="flex flex-wrap gap-1.5">
                    {stats.card_sequence.map((play, i) => {
                      // Show turn separator
                      const showTurnMarker =
                        i === 0 ||
                        play.turn !== stats.card_sequence[i - 1].turn;
                      return (
                        <React.Fragment key={i}>
                          {showTurnMarker && (
                            <div className="flex items-center mr-1">
                              {i > 0 && (
                                <div className="w-px h-6 bg-sts-border mx-2" />
                              )}
                              <span className="text-xs text-sts-text font-mono">
                                T{play.turn}
                              </span>
                            </div>
                          )}
                          <span
                            className="inline-block px-2 py-1 bg-sts-surface rounded text-xs font-medium text-sts-gold-light border border-sts-border/50"
                            title={
                              play.target
                                ? `Target: ${formatGameId(play.target)}`
                                : "No target"
                            }
                          >
                            {formatGameId(play.card)}
                          </span>
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
