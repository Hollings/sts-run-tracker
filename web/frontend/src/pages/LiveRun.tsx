import React, { useState, useEffect } from "react";
import type {
  MergedLiveData,
  Combat,
  Floor,
  FloorPlayer,
  PlayerRunTotals,
} from "../utils/types";
import { formatGameId } from "../utils/format";
import CombatDetail from "../components/CombatDetail";

interface Props {
  data: MergedLiveData | null;
}

// ---------------------------------------------------------------------------
// Floor type helpers
// ---------------------------------------------------------------------------

const FLOOR_TYPE_LABELS: Record<string, string> = {
  monster: "Monster",
  elite: "Elite",
  boss: "Boss",
  ancient: "Ancient",
  unknown: "Event",
  rest_site: "Rest",
  treasure: "Treasure",
  shop: "Shop",
  event: "Event",
};

const FLOOR_TYPE_ICONS: Record<string, string> = {
  monster: "M",
  elite: "E",
  boss: "B",
  ancient: "A",
  unknown: "?",
  rest_site: "R",
  treasure: "T",
  shop: "$",
  event: "?",
};

function floorTypeBorderColor(type: string): string {
  switch (type) {
    case "monster":
      return "border-red-700/60";
    case "elite":
      return "border-amber-600/60";
    case "boss":
      return "border-purple-600/60";
    case "ancient":
      return "border-purple-500/60";
    case "rest_site":
      return "border-green-600/60";
    case "treasure":
      return "border-yellow-500/60";
    case "shop":
      return "border-emerald-600/60";
    default:
      return "border-blue-600/60";
  }
}

function floorTypeBgColor(type: string): string {
  switch (type) {
    case "monster":
      return "bg-red-900/25";
    case "elite":
      return "bg-amber-900/25";
    case "boss":
      return "bg-purple-900/25";
    case "ancient":
      return "bg-purple-900/20";
    case "rest_site":
      return "bg-green-900/20";
    case "treasure":
      return "bg-yellow-900/20";
    case "shop":
      return "bg-emerald-900/20";
    default:
      return "bg-blue-900/20";
  }
}

function floorTypeTextColor(type: string): string {
  switch (type) {
    case "monster":
      return "text-red-400";
    case "elite":
      return "text-amber-400";
    case "boss":
      return "text-purple-400";
    case "ancient":
      return "text-purple-300";
    case "rest_site":
      return "text-green-400";
    case "treasure":
      return "text-yellow-400";
    case "shop":
      return "text-emerald-400";
    default:
      return "text-blue-400";
  }
}

const isCombatFloor = (type: string) =>
  type === "monster" || type === "elite" || type === "boss";

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function LiveRun({ data }: Props) {
  const [expandedFloor, setExpandedFloor] = useState<number | null>(null);

  // Auto-expand latest combat floor when new data arrives
  useEffect(() => {
    if (data && data.floors.length > 0) {
      // Find the last combat floor
      for (let i = data.floors.length - 1; i >= 0; i--) {
        if (data.floors[i].combat) {
          setExpandedFloor(data.floors[i].floor);
          return;
        }
      }
      // If no combat floors, expand last floor
      setExpandedFloor(data.floors[data.floors.length - 1].floor);
    }
  }, [data?.floors.length]);

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-sts-text-dim">
        <div className="text-6xl mb-4 text-sts-gold-dim">?</div>
        <h2 className="text-xl font-semibold mb-2">Waiting for Data</h2>
        <p className="text-sm">
          Start a run in Slay the Spire 2 with the tracker mod enabled.
        </p>
        <p className="text-sm mt-1">
          Combat data will appear here automatically via WebSocket.
        </p>
      </div>
    );
  }

  const { floors, combats, run_info, run_totals } = data;
  const latestFloor = floors[floors.length - 1] as Floor | undefined;
  const playerEntries = run_totals?.players
    ? Object.entries(run_totals.players)
    : [];

  // Compute aggregate damage totals from run_totals
  let totalDamage = 0;
  let totalTaken = 0;
  for (const [, pt] of playerEntries) {
    totalDamage += pt.damage_dealt;
    totalTaken += pt.damage_taken;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header bar */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-sts-gold">
              {run_info?.seed || "Live Run"}
            </h1>
            <p className="text-sm text-sts-text-dim mt-1">
              {run_info?.ascension != null && run_info.ascension > 0
                ? `Ascension ${run_info.ascension} | `
                : ""}
              {run_info?.players
                ?.map((p) => formatGameId(p.character))
                .join(" & ")}
            </p>
          </div>
          <div className="flex flex-wrap gap-6 text-center">
            <StatBox label="Floors" value={floors.length} />
            <StatBox
              label="Combats"
              value={run_totals?.total_combats ?? combats.length}
            />
            <StatBox
              label="Current Floor"
              value={latestFloor?.floor ?? 0}
            />
            <StatBox
              label="Total Damage"
              value={totalDamage}
              color="text-sts-red"
            />
            <StatBox
              label="Total Taken"
              value={totalTaken}
              color="text-orange-400"
            />
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main content - floor timeline */}
        <div className="flex-1 space-y-3">
          {/* Floor mini-map */}
          <div className="bg-sts-surface border border-sts-border rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-sts-text-dim mb-3">
              Floor Timeline
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {floors.map((floor) => {
                const isExpanded = expandedFloor === floor.floor;
                return (
                  <button
                    key={floor.floor}
                    onClick={() =>
                      setExpandedFloor(isExpanded ? null : floor.floor)
                    }
                    className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold border-2 transition-all ${
                      isExpanded
                        ? "border-sts-gold scale-110"
                        : "border-transparent"
                    } ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(
                      floor.type
                    )} hover:brightness-125`}
                    title={`Floor ${floor.floor}: ${
                      FLOOR_TYPE_LABELS[floor.type] || floor.type
                    } - ${floor.room_id || "?"}`}
                  >
                    {floor.floor}
                  </button>
                );
              })}
            </div>
            {/* Legend */}
            <div className="flex flex-wrap gap-3 mt-3 text-xs text-sts-text-dim">
              {["monster", "elite", "boss", "rest_site", "treasure", "shop", "unknown"].map((t) => (
                <span key={t} className="flex items-center gap-1">
                  <span
                    className={`inline-block w-3 h-3 rounded ${floorTypeBgColor(
                      t
                    )} ${floorTypeBorderColor(t)} border`}
                  />
                  {FLOOR_TYPE_LABELS[t] || t}
                </span>
              ))}
            </div>
          </div>

          {/* Floor details */}
          <h3 className="text-lg font-semibold text-sts-text mb-2">
            Floors
          </h3>
          {floors.map((floor) => (
            <FloorCard
              key={floor.floor}
              floor={floor}
              expanded={expandedFloor === floor.floor}
              onToggle={() =>
                setExpandedFloor(
                  expandedFloor === floor.floor ? null : floor.floor
                )
              }
            />
          ))}
        </div>

        {/* Run totals sidebar */}
        <div className="lg:w-80 space-y-4">
          <div className="bg-sts-surface border border-sts-border rounded-lg p-4 lg:sticky lg:top-20">
            <h3 className="text-lg font-semibold text-sts-gold mb-4">
              Run Totals
            </h3>

            {playerEntries.length === 0 && (
              <p className="text-sm text-sts-text-dim">
                No combat data yet.
              </p>
            )}

            {playerEntries.map(([pid, pt]) => (
              <div key={pid} className="mb-5 last:mb-0">
                <h4 className="text-sm font-semibold text-sts-gold-light mb-2">
                  {formatGameId(pt.character)}
                </h4>
                <div className="space-y-1.5 text-sm">
                  <TotalRow
                    label="Damage Dealt"
                    value={pt.damage_dealt}
                    color="text-sts-red"
                  />
                  <TotalRow
                    label="Damage Taken"
                    value={pt.damage_taken}
                    color="text-orange-400"
                  />
                  <TotalRow
                    label="Block Gained"
                    value={pt.block_gained}
                    color="text-sts-blue"
                  />
                  <TotalRow
                    label="Cards Played"
                    value={pt.cards_played}
                  />
                  <TotalRow
                    label="Kills"
                    value={pt.kills}
                    color="text-sts-red"
                  />
                  <TotalRow
                    label="Combats"
                    value={pt.combats}
                  />

                  {/* Best Hit - shown prominently */}
                  {pt.best_hit && pt.best_hit.damage > 0 && (
                    <BestHitDisplay bestHit={pt.best_hit} />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Best Hit display
// ---------------------------------------------------------------------------

function BestHitDisplay({
  bestHit,
}: {
  bestHit: { card: string; damage: number; encounter: string };
}) {
  return (
    <div className="mt-3 pt-3 border-t border-sts-border/50">
      <div className="text-xs text-sts-text-dim uppercase tracking-wide mb-1">
        Best Single Hit
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-black text-sts-amber">
          {bestHit.damage}
        </span>
        <span className="text-sm text-sts-text-dim">dmg</span>
      </div>
      <div className="text-sm mt-0.5">
        <span className="text-sts-gold-light font-medium">
          {bestHit.card}
        </span>
        {bestHit.encounter && (
          <span className="text-sts-text-dim ml-1">
            vs {bestHit.encounter}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Floor card component
// ---------------------------------------------------------------------------

function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className || "w-5 h-5"}
    >
      <path
        fillRule="evenodd"
        d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function FloorCard({
  floor,
  expanded,
  onToggle,
}: {
  floor: Floor;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasCombat = !!floor.combat;
  const typeLabel = FLOOR_TYPE_LABELS[floor.type] || floor.type;
  const icon = FLOOR_TYPE_ICONS[floor.type] || "?";

  return (
    <div
      className={`border rounded-lg overflow-hidden ${floorTypeBorderColor(
        floor.type
      )} bg-sts-surface`}
    >
      {/* Header - always visible */}
      <div className="px-4 py-3 flex items-center justify-between text-left">
        <div className="flex items-center gap-3">
          {/* Type badge */}
          <span
            className={`inline-flex items-center justify-center w-8 h-8 rounded-md text-xs font-bold ${floorTypeBgColor(
              floor.type
            )} ${floorTypeTextColor(floor.type)} border ${floorTypeBorderColor(
              floor.type
            )}`}
          >
            {icon}
          </span>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sts-gold">
                Floor {floor.floor}
              </span>
              <span className={`text-xs font-medium ${floorTypeTextColor(floor.type)}`}>
                {typeLabel}
              </span>
            </div>
            <div className="text-sm text-sts-text">
              {floor.room_id || "Unknown Room"}
              {floor.monsters.length > 0 && (
                <span className="text-sts-text-dim ml-2">
                  vs {floor.monsters.join(", ")}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm">
          {/* Player HP summary in header */}
          {floor.players.map((p, i) => (
            <span key={i} className="text-sts-text-dim">
              <span className="text-sts-red">{p.hp}</span>
              <span className="text-sts-text-dim">/{p.max_hp}</span>
              {p.gold > 0 && (
                <span className="ml-2 text-yellow-400">{p.gold}g</span>
              )}
            </span>
          ))}
          {hasCombat && floor.combat && (
            <span
              className={
                floor.combat.result === "in_progress"
                  ? "text-yellow-400 font-bold"
                  : floor.combat.result === "win"
                  ? "text-sts-green font-bold"
                  : "text-sts-red font-bold"
              }
            >
              {floor.combat.result === "in_progress" ? "FIGHTING" : floor.combat.result === "win" ? "WIN" : "LOSS"}
            </span>
          )}
        </div>
      </div>

      {/* Per-player floor stats - always visible */}
      <div className="px-4 pb-3">
        <div
          className={`grid gap-3 ${
            floor.players.length > 1 ? "md:grid-cols-2" : "grid-cols-1"
          }`}
        >
          {floor.players.map((p, i) => (
            <FloorPlayerCard key={i} player={p} floorType={floor.type} />
          ))}
        </div>
      </div>

      {/* Expand/collapse button for combat floors */}
      {hasCombat && (
        <button
          className="w-full px-4 py-2 flex items-center justify-center gap-2 text-sm font-medium text-sts-gold-light hover:bg-sts-card/50 border-t border-sts-border/50 transition-colors"
          onClick={onToggle}
        >
          <span>{expanded ? "Hide Combat Detail" : "Show Combat Detail"}</span>
          <ChevronDown
            className={`w-4 h-4 transition-transform duration-200 ${
              expanded ? "rotate-180" : ""
            }`}
          />
        </button>
      )}

      {/* Expanded combat detail */}
      {hasCombat && expanded && floor.combat && (
        <div className="px-4 pb-4 pt-2 border-t border-sts-border/50 space-y-4">
          <CombatDetail
            combat={floor.combat}
            index={floor.floor}
            expanded={true}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Floor player card
// ---------------------------------------------------------------------------

function FloorPlayerCard({
  player,
  floorType,
}: {
  player: FloorPlayer;
  floorType: string;
}) {
  const hpPct = player.max_hp > 0 ? (player.hp / player.max_hp) * 100 : 0;
  const hpColor =
    hpPct > 60 ? "bg-sts-green" : hpPct > 30 ? "bg-yellow-500" : "bg-sts-red";

  return (
    <div className="bg-sts-card rounded-lg p-3 space-y-2">
      {/* HP bar */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-sts-text-dim">
            Player {player.player_id}
          </span>
          <span>
            <span className="text-sts-red font-semibold">{player.hp}</span>
            <span className="text-sts-text-dim">/{player.max_hp}</span>
          </span>
        </div>
        <div className="h-2 bg-sts-surface rounded-full overflow-hidden">
          <div
            className={`h-full ${hpColor} rounded-full transition-all`}
            style={{ width: `${hpPct}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {player.damage_taken > 0 && (
          <span>
            <span className="text-sts-text-dim">Dmg Taken: </span>
            <span className="text-orange-400 font-semibold">
              {player.damage_taken}
            </span>
          </span>
        )}
        {player.hp_healed > 0 && (
          <span>
            <span className="text-sts-text-dim">Healed: </span>
            <span className="text-sts-green font-semibold">
              {player.hp_healed}
            </span>
          </span>
        )}
        <span>
          <span className="text-sts-text-dim">Gold: </span>
          <span className="text-yellow-400 font-semibold">{player.gold}</span>
        </span>
        {player.gold_gained > 0 && (
          <span className="text-yellow-400/70">+{player.gold_gained}</span>
        )}
        {player.gold_spent > 0 && (
          <span className="text-orange-400/70">-{player.gold_spent}</span>
        )}
      </div>

      {/* Cards picked */}
      {player.cards_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text-dim">Picked: </span>
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
          <span className="text-sts-text-dim">Skipped: </span>
          {player.cards_skipped.map((c, i) => (
            <span
              key={i}
              className="inline-block px-1.5 py-0.5 bg-sts-surface text-sts-text-dim rounded mr-1 mb-0.5"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Relics picked */}
      {player.relics_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text-dim">Relics: </span>
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

      {/* Potions picked */}
      {player.potions_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text-dim">Potions: </span>
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

      {/* Event choices */}
      {player.event_choices.length > 0 &&
        player.event_choices.some((e) => e) && (
          <div className="text-xs">
            <span className="text-sts-text-dim">Event: </span>
            {player.event_choices
              .filter((e) => e)
              .map((e, i) => (
                <span
                  key={i}
                  className="inline-block px-1.5 py-0.5 bg-blue-900/20 text-blue-300 rounded mr-1 mb-0.5"
                >
                  {e}
                </span>
              ))}
          </div>
        )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared UI helpers
// ---------------------------------------------------------------------------

function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div>
      <div className={`text-2xl font-bold ${color || "text-sts-text"}`}>
        {value}
      </div>
      <div className="text-xs text-sts-text-dim">{label}</div>
    </div>
  );
}

function TotalRow({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-sts-text-dim">{label}</span>
      <span className={`font-mono font-semibold ${color || "text-sts-text"}`}>
        {value}
      </span>
    </div>
  );
}
