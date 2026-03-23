import React, { useState, useEffect } from "react";
import type {
  MergedLiveData,
  Combat,
  Floor,
  FloorPlayer,
  PlayerCombatStats,
  PlayerRunTotals,
} from "../utils/types";
import { formatGameId } from "../utils/format";
import DamageChart from "../components/DamageChart";

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
    case "monster": return "border-[#8B1913]/50";
    case "elite": return "border-[#a86830]/50";
    case "boss": return "border-[#7a3a5a]/50";
    case "ancient": return "border-[#6a4a7a]/50";
    case "rest_site": return "border-[#3a6a4a]/50";
    case "treasure": return "border-[#776754]/50";
    case "shop": return "border-[#3a6a5a]/50";
    default: return "border-sts-border";
  }
}

function floorTypeBgColor(type: string): string {
  switch (type) {
    case "monster": return "bg-[#8B1913]/15";
    case "elite": return "bg-[#a86830]/15";
    case "boss": return "bg-[#7a3a5a]/15";
    case "ancient": return "bg-[#6a4a7a]/15";
    case "rest_site": return "bg-[#3a6a4a]/15";
    case "treasure": return "bg-[#776754]/15";
    case "shop": return "bg-[#3a6a5a]/15";
    default: return "bg-sts-card/30";
  }
}

function floorTypeTextColor(type: string): string {
  switch (type) {
    case "monster": return "text-[#e05550]";
    case "elite": return "text-[#d4943a]";
    case "boss": return "text-[#c47aa0]";
    case "ancient": return "text-[#a07ac0]";
    case "rest_site": return "text-[#5aaa6a]";
    case "treasure": return "text-[#c4b888]";
    case "shop": return "text-[#5aaa8a]";
    default: return "text-sts-text";
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function LiveRun({ data }: Props) {
  const [selectedFloor, setSelectedFloor] = useState<number | null>(null);
  const [showSummary, setShowSummary] = useState(false);

  // Detect run completion: last floor is a boss win
  const isRunComplete = data
    ? (() => {
        const last = data.floors[data.floors.length - 1];
        return last?.type === "boss" && last?.combat?.result === "win";
      })()
    : false;

  // Auto-select latest floor when new data arrives
  useEffect(() => {
    if (data && data.floors.length > 0 && selectedFloor === null) {
      setSelectedFloor(data.floors[data.floors.length - 1].floor);
    }
  }, [data?.floors.length]);

  // When new floors appear, snap to live
  useEffect(() => {
    if (data && data.floors.length > 0) {
      const latest = data.floors[data.floors.length - 1];
      if (latest.combat?.result === "in_progress") {
        setSelectedFloor(latest.floor);
        setShowSummary(false);
      }
    }
  }, [data?.combats.length]);

  // Auto-show summary on run completion
  useEffect(() => {
    if (isRunComplete) setShowSummary(true);
  }, [isRunComplete]);

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-sts-text">
        <div className="text-6xl mb-4 text-sts-gold-dim">?</div>
        <h2 className="text-xl font-semibold mb-2">Waiting for Data</h2>
        <p className="text-sm">
          Start a run in Slay the Spire 2 with the tracker mod enabled.
        </p>
      </div>
    );
  }

  const { floors, combats, run_info, run_totals } = data;
  const latestFloor = floors[floors.length - 1] as Floor | undefined;
  const activeFloor = floors.find((f) => f.floor === selectedFloor) || latestFloor;
  const isLiveView = activeFloor === latestFloor;
  const playerEntries = run_totals?.players
    ? Object.entries(run_totals.players)
    : [];

  let totalDamage = 0;
  let totalTaken = 0;
  for (const [, pt] of playerEntries) {
    totalDamage += pt.damage_dealt;
    totalTaken += pt.damage_taken;
  }

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">
      {/* Top bar */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-3 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-lg font-bold text-sts-gold">
                {run_info?.seed || "Live Run"}
              </span>
              <span className="text-sm text-sts-text ml-3">
                {run_info?.ascension != null && run_info.ascension > 0
                  ? `A${run_info.ascension} `
                  : ""}
                {run_info?.players
                  ?.map((p) => formatGameId(p.character))
                  .join(" & ")}
              </span>
            </div>
          </div>
          <div className="flex gap-6 text-center">
            <TopStat label="Floor" value={latestFloor?.floor ?? 0} />
            <TopStat label="Combats" value={run_totals?.total_combats ?? combats.length} />
            <TopStat label="Damage" value={totalDamage} color="text-sts-red" />
            <TopStat label="Taken" value={totalTaken} color="text-orange-400" />
          </div>
        </div>
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 140px)" }}>
        {/* Left 2/3 - Detail view */}
        <div className="flex-1 min-w-0 flex flex-col">
          {showSummary ? (
            <RunSummaryView
              data={data}
              onClose={() => setShowSummary(false)}
            />
          ) : activeFloor ? (
            <FloorDetailView
              floor={activeFloor}
              isLive={isLiveView}
              onGoLive={() => setSelectedFloor(latestFloor?.floor ?? null)}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-sts-text">
              Select a floor from the sidebar
            </div>
          )}
        </div>

        {/* Right 1/3 - Sidebar */}
        <div className="w-80 flex flex-col min-h-0 gap-4">
          {/* Run totals */}
          <div className="bg-sts-surface border border-sts-border rounded-lg p-3 shrink-0">
            <h3 className="text-sm font-semibold text-sts-gold mb-2">Run Totals</h3>
            {playerEntries.length === 0 ? (
              <p className="text-xs text-sts-text">No combat data yet.</p>
            ) : (
              <div className="space-y-2">
                {playerEntries.map(([pid, pt]) => (
                  <RunTotalCard key={pid} player={pt} />
                ))}
              </div>
            )}
          </div>

          {/* Summary button */}
          {isRunComplete && (
            <button
              onClick={() => setShowSummary(true)}
              className={`w-full py-2.5 rounded-lg text-sm font-bold shrink-0 ${
                showSummary
                  ? "bg-sts-gold/20 text-sts-gold border border-sts-gold/30"
                  : "bg-sts-green/20 text-sts-green border border-sts-green/30 hover:bg-sts-green/30"
              }`}
            >
              VICTORY - View Summary
            </button>
          )}

          {/* Floor list */}
          <div className="bg-sts-surface border border-sts-border rounded-lg flex-1 min-h-0 flex flex-col">
            <h3 className="text-sm font-semibold text-sts-gold p-3 pb-2 shrink-0">
              Floors
            </h3>
            <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-1">
              {[...floors].reverse().map((floor, i) => (
                <SidebarFloorItem
                  key={floor.floor}
                  floor={floor}
                  isLive={i === 0}
                  isSelected={selectedFloor === floor.floor}
                  onClick={() => setSelectedFloor(floor.floor)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top bar stat
// ---------------------------------------------------------------------------

function TopStat({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div>
      <div className={`text-xl font-bold ${color || "text-sts-text"}`}>{value}</div>
      <div className="text-[10px] text-sts-text uppercase tracking-wide">{label}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Run Summary (victory screen)
// ---------------------------------------------------------------------------

function RunSummaryView({ data, onClose }: { data: MergedLiveData; onClose: () => void }) {
  const { combats, run_totals, floors } = data;
  const playerEntries = run_totals?.players
    ? Object.entries(run_totals.players)
    : [];

  // Aggregate card play counts from all combats
  const cardPlays: Record<string, number> = {};
  const cardDamage: Record<string, { total_damage: number; hits: number; max_hit: number; kills: number }> = {};
  for (const c of combats) {
    for (const stats of Object.values(c.players)) {
      for (const play of stats.card_sequence) {
        cardPlays[play.card] = (cardPlays[play.card] || 0) + 1;
      }
      for (const [cardId, cs] of Object.entries(stats.damage_by_card)) {
        if (!cardDamage[cardId]) {
          cardDamage[cardId] = { total_damage: 0, hits: 0, max_hit: 0, kills: 0 };
        }
        cardDamage[cardId].total_damage += cs.total_damage;
        cardDamage[cardId].hits += cs.hits;
        cardDamage[cardId].max_hit = Math.max(cardDamage[cardId].max_hit, cs.max_hit);
        cardDamage[cardId].kills += cs.kills;
      }
    }
  }

  // Compute fun facts
  const totalPlays = Object.values(cardPlays).reduce((a, b) => a + b, 0);
  const totalPartyDamage = playerEntries.reduce((a, [, p]) => a + p.damage_dealt, 0);
  const totalPartyTaken = playerEntries.reduce((a, [, p]) => a + p.damage_taken, 0);
  const totalPartyBlock = playerEntries.reduce((a, [, p]) => a + p.block_gained, 0);
  const totalKills = playerEntries.reduce((a, [, p]) => a + p.kills, 0);

  // Most played card
  const mostPlayed = Object.entries(cardPlays).sort((a, b) => b[1] - a[1])[0];
  // Most damage card
  const mostDamage = Object.entries(cardDamage).filter(([id]) => id !== "_non_card").sort((a, b) => b[1].total_damage - a[1].total_damage)[0];
  // Most kills card
  const mostKills = Object.entries(cardDamage).filter(([id]) => id !== "_non_card").sort((a, b) => b[1].kills - a[1].kills)[0];
  // Best single hit across all players
  const bestHit = playerEntries.reduce(
    (best, [, p]) => p.best_hit && p.best_hit.damage > best.damage
      ? { ...p.best_hit, character: p.character }
      : best,
    { card: "", damage: 0, encounter: "", character: "" },
  );
  // MVP (most damage dealt)
  const mvp = playerEntries.sort((a, b) => b[1].damage_dealt - a[1].damage_dealt)[0];
  // Tank (most damage taken)
  const tank = playerEntries.sort((a, b) => b[1].damage_taken - a[1].damage_taken)[0];

  const factCards: { title: string; value: string; detail: string; color: string }[] = [];

  if (mostPlayed) {
    factCards.push({
      title: "Most Played Card",
      value: formatGameId(mostPlayed[0]),
      detail: `${mostPlayed[1]} plays (${Math.round(mostPlayed[1] / totalPlays * 100)}% of all cards)`,
      color: "text-sts-gold",
    });
  }
  if (mostDamage) {
    factCards.push({
      title: "Highest Damage Card",
      value: formatGameId(mostDamage[0]),
      detail: `${mostDamage[1].total_damage} total damage across ${mostDamage[1].hits} hits`,
      color: "text-sts-red",
    });
  }
  if (bestHit.damage > 0) {
    factCards.push({
      title: "Biggest Single Hit",
      value: `${bestHit.damage} damage`,
      detail: `${bestHit.card} vs ${bestHit.encounter}`,
      color: "text-sts-amber",
    });
  }
  if (mostKills && mostKills[1].kills > 0) {
    factCards.push({
      title: "Deadliest Card",
      value: formatGameId(mostKills[0]),
      detail: `${mostKills[1].kills} killing blows`,
      color: "text-red-400",
    });
  }
  if (mvp) {
    factCards.push({
      title: "MVP",
      value: formatGameId(mvp[1].character),
      detail: `${mvp[1].damage_dealt} damage dealt, ${mvp[1].kills} kills`,
      color: "text-purple-400",
    });
  }
  if (tank && playerEntries.length > 1) {
    factCards.push({
      title: "Tank",
      value: formatGameId(tank[1].character),
      detail: `${tank[1].damage_taken} damage absorbed, ${tank[1].block_gained} block gained`,
      color: "text-sts-blue",
    });
  }

  return (
    <div className="flex flex-col h-full gap-4 overflow-y-auto">
      {/* Victory header */}
      <div className="bg-sts-surface border border-sts-green/30 rounded-lg p-6 text-center shrink-0">
        <div className="text-4xl font-black text-sts-green mb-2">VICTORY</div>
        <p className="text-sts-text">
          {floors.length} floors | {combats.length} combats | {totalKills} kills
        </p>
        <button
          onClick={onClose}
          className="mt-3 px-4 py-1.5 text-xs text-sts-text hover:text-sts-text border border-sts-border rounded hover:bg-sts-card/50"
        >
          View Floor Details
        </button>
      </div>

      {/* Party totals */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4 shrink-0">
        <h3 className="text-sm font-semibold text-sts-text mb-3">Party Totals</h3>
        <div className="grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-sts-red">{totalPartyDamage}</div>
            <div className="text-xs text-sts-text">Damage Dealt</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-orange-400">{totalPartyTaken}</div>
            <div className="text-xs text-sts-text">Damage Taken</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-sts-blue">{totalPartyBlock}</div>
            <div className="text-xs text-sts-text">Block Gained</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-sts-text">{totalPlays}</div>
            <div className="text-xs text-sts-text">Cards Played</div>
          </div>
        </div>
      </div>

      {/* Fun fact cards */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {factCards.map((fact, i) => (
          <div key={i} className="bg-sts-surface border border-sts-border rounded-lg p-4">
            <div className="text-[10px] uppercase tracking-wider text-sts-text mb-1">
              {fact.title}
            </div>
            <div className={`text-xl font-bold ${fact.color} mb-1`}>
              {fact.value}
            </div>
            <div className="text-xs text-sts-text">{fact.detail}</div>
          </div>
        ))}
      </div>

      {/* Per-player breakdown */}
      <div className={`grid gap-3 shrink-0 ${playerEntries.length > 2 ? "grid-cols-3" : playerEntries.length > 1 ? "grid-cols-2" : "grid-cols-1"}`}>
        {playerEntries.map(([pid, pt]) => {
          const playerCards = Object.entries(cardDamage)
            .filter(([id]) => id !== "_non_card")
            .sort((a, b) => b[1].total_damage - a[1].total_damage)
            .slice(0, 5);
          return (
            <div key={pid} className="bg-sts-surface border border-sts-border rounded-lg p-4">
              <h4 className="text-sm font-semibold text-sts-gold mb-2">
                {formatGameId(pt.character)}
              </h4>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs mb-3">
                <StatRow label="Damage" value={pt.damage_dealt} color="text-sts-red" />
                <StatRow label="Taken" value={pt.damage_taken} color="text-orange-400" />
                <StatRow label="Block" value={pt.block_gained} color="text-sts-blue" />
                <StatRow label="Kills" value={pt.kills} color="text-sts-text" />
              </div>
              {pt.best_hit && pt.best_hit.damage > 0 && (
                <div className="text-xs border-t border-sts-border/50 pt-2">
                  <span className="text-sts-text">Best: </span>
                  <span className="text-sts-amber font-bold">{pt.best_hit.damage}</span>
                  <span className="text-sts-text"> with </span>
                  <span className="text-sts-gold-light">{pt.best_hit.card}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main detail view (left 2/3)
// ---------------------------------------------------------------------------

function FloorDetailView({
  floor,
  isLive,
  onGoLive,
}: {
  floor: Floor;
  isLive: boolean;
  onGoLive: () => void;
}) {
  const combat = floor.combat;
  const typeLabel = FLOOR_TYPE_LABELS[floor.type] || floor.type;
  const playerEntries = combat ? Object.entries(combat.players) : [];

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Floor header */}
      <div className={`bg-sts-surface border rounded-lg p-4 shrink-0 ${
        isLive && combat?.result === "in_progress"
          ? "border-yellow-500/80 ring-1 ring-yellow-500/30"
          : "border-sts-border"
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center justify-center w-10 h-10 rounded-lg text-sm font-bold ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(floor.type)} border ${floorTypeBorderColor(floor.type)}`}>
              {floor.floor}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-sts-gold">
                  {floor.room_id || "Unknown"}
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(floor.type)}`}>
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
              <span className={`text-lg font-bold ${
                combat.result === "in_progress" ? "text-yellow-400"
                  : combat.result === "win" ? "text-sts-green"
                  : "text-sts-red"
              }`}>
                {combat.result === "in_progress" ? "FIGHTING"
                  : combat.result === "win" ? "WIN" : "LOSS"}
              </span>
            )}
            {!isLive && (
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
          {/* Player cards grid */}
          <div className={`grid gap-3 shrink-0 ${playerEntries.length > 2 ? "grid-cols-3" : playerEntries.length > 1 ? "grid-cols-2" : "grid-cols-1"}`}>
            {playerEntries.map(([pid, stats]) => (
              <CombatPlayerCard key={pid} playerId={pid} stats={stats} />
            ))}
          </div>

          {/* Per-turn chart - combined party view */}
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
        /* Non-combat floor */
        <div className="flex-1 bg-sts-surface border border-sts-border rounded-lg p-4">
          <div className={`grid gap-3 ${floor.players.length > 1 ? "md:grid-cols-2" : "grid-cols-1"}`}>
            {floor.players.map((p, i) => (
              <NonCombatPlayerCard key={i} player={p} floorType={floor.type} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Combat player card (main view)
// ---------------------------------------------------------------------------

function CombatPlayerCard({ playerId, stats }: { playerId: string; stats: PlayerCombatStats }) {
  const cardEntries = Object.entries(stats.damage_by_card || {})
    .sort(([, a], [, b]) => b.total_damage - a.total_damage)
    .slice(0, 4);

  return (
    <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
      <h4 className="text-sm font-semibold text-sts-gold mb-3">
        {formatGameId(stats.character)}
      </h4>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-3">
        <StatRow label="Damage" value={stats.damage_dealt} color="text-sts-red" />
        <StatRow label="Taken" value={stats.damage_taken} color="text-orange-400" />
        <StatRow label="Block" value={stats.block_gained} color="text-sts-blue" />
        <StatRow label="Cards" value={stats.cards_played} color="text-sts-text" />
      </div>

      {/* Top cards */}
      {cardEntries.length > 0 && (
        <div className="border-t border-sts-border/50 pt-2 space-y-1">
          {cardEntries.map(([cardId, dmg]) => (
            <div key={cardId} className="flex justify-between text-xs">
              <span className="text-sts-gold-light truncate mr-2">
                {formatGameId(cardId)}
              </span>
              <span className="text-sts-text font-mono whitespace-nowrap">
                {dmg.total_damage}
                <span className="text-sts-text/50 ml-1">
                  ({dmg.hits}x)
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-xs text-sts-text">{label}</span>
      <span className={`text-lg font-bold ${color}`}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Non-combat floor player card
// ---------------------------------------------------------------------------

function NonCombatPlayerCard({ player, floorType }: { player: FloorPlayer; floorType: string }) {
  const hpPct = player.max_hp > 0 ? (player.hp / player.max_hp) * 100 : 0;
  const hpColor = hpPct > 60 ? "bg-sts-green" : hpPct > 30 ? "bg-yellow-500" : "bg-sts-red";

  const restChoices = player.rest_site_choices ?? [];
  const upgradedCards = player.upgraded_cards ?? [];
  const eventChoices = player.event_choices ?? [];
  const hasAnyDetail = restChoices.length > 0 || upgradedCards.length > 0
    || eventChoices.some(e => e) || player.cards_picked.length > 0
    || player.cards_skipped.length > 0 || player.relics_picked.length > 0
    || player.potions_picked.length > 0 || player.gold_spent > 0
    || player.gold_gained > 0 || player.damage_taken > 0 || player.hp_healed > 0;

  return (
    <div className="bg-sts-card rounded-lg p-3 space-y-2">
      {/* Header: HP + Gold */}
      <div className="flex justify-between text-xs mb-1">
        <span className="text-sts-text">Player {player.player_id}</span>
        <span>
          <span className="text-sts-red font-semibold">{player.hp}</span>
          <span className="text-sts-text">/{player.max_hp}</span>
          <span className="text-yellow-400 ml-2">{player.gold}g</span>
        </span>
      </div>
      <div className="h-2 bg-sts-surface rounded-full overflow-hidden">
        <div className={`h-full ${hpColor} rounded-full`} style={{ width: `${hpPct}%` }} />
      </div>

      {/* HP changes */}
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

      {/* Gold changes */}
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

      {/* Rest site actions */}
      {restChoices.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Rest action: </span>
          {restChoices.map((c, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-green-900/30 text-green-400 rounded mr-1 font-medium">{c}</span>
          ))}
        </div>
      )}

      {/* Upgraded cards */}
      {upgradedCards.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Upgraded: </span>
          {upgradedCards.map((c, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-sts-gold/10 text-sts-gold-light rounded mr-1 font-medium">{c}</span>
          ))}
        </div>
      )}

      {/* Event choices */}
      {eventChoices.length > 0 && eventChoices.some(e => e) && (
        <div className="text-xs">
          <span className="text-sts-text">Chose: </span>
          {eventChoices.filter(e => e).map((e, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-blue-900/20 text-blue-300 rounded mr-1 font-medium">{e}</span>
          ))}
        </div>
      )}

      {/* Cards picked */}
      {player.cards_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Picked: </span>
          {player.cards_picked.map((c, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-green-900/30 text-sts-green rounded mr-1 mb-0.5 font-medium">{c}</span>
          ))}
        </div>
      )}

      {/* Cards skipped (shops) */}
      {player.cards_skipped.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Available: </span>
          {player.cards_skipped.map((c, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-sts-surface text-sts-text rounded mr-1 mb-0.5">{c}</span>
          ))}
        </div>
      )}

      {/* Relics */}
      {player.relics_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Relics: </span>
          {player.relics_picked.map((r, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-amber-900/30 text-sts-amber rounded mr-1 mb-0.5 font-medium">{r}</span>
          ))}
        </div>
      )}

      {/* Potions */}
      {player.potions_picked.length > 0 && (
        <div className="text-xs">
          <span className="text-sts-text">Potions: </span>
          {player.potions_picked.map((p, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-blue-900/30 text-sts-blue rounded mr-1 mb-0.5 font-medium">{p}</span>
          ))}
        </div>
      )}

      {!hasAnyDetail && (
        <div className="text-xs text-sts-text">No changes this floor</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar: Run total card
// ---------------------------------------------------------------------------

function RunTotalCard({ player }: { player: PlayerRunTotals }) {
  return (
    <div className="bg-sts-card rounded-lg p-2.5 border border-sts-border/30">
      <div className="text-xs font-semibold text-sts-gold-light mb-1.5">
        {formatGameId(player.character)}
      </div>
      <div className="grid grid-cols-3 gap-1 text-center text-xs">
        <div>
          <div className="text-sts-red font-bold">{player.damage_dealt}</div>
          <div className="text-[10px] text-sts-text">Dealt</div>
        </div>
        <div>
          <div className="text-orange-400 font-bold">{player.damage_taken}</div>
          <div className="text-[10px] text-sts-text">Taken</div>
        </div>
        <div>
          <div className="text-sts-blue font-bold">{player.block_gained}</div>
          <div className="text-[10px] text-sts-text">Block</div>
        </div>
      </div>
      {player.best_hit && player.best_hit.damage > 0 && (
        <div className="mt-1.5 pt-1.5 border-t border-sts-border/30 text-[10px] text-sts-text">
          Best: <span className="text-sts-amber font-bold">{player.best_hit.damage}</span> with <span className="text-sts-gold-light">{player.best_hit.card}</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar: Floor item
// ---------------------------------------------------------------------------

function SidebarFloorItem({
  floor,
  isLive,
  isSelected,
  onClick,
}: {
  floor: Floor;
  isLive: boolean;
  isSelected: boolean;
  onClick: () => void;
}) {
  const combat = floor.combat;
  const icon = FLOOR_TYPE_ICONS[floor.type] || "?";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-2.5 py-1.5 rounded-md flex items-center gap-2 text-xs ${
        isSelected
          ? "bg-sts-gold/10 border border-sts-gold/30"
          : "hover:bg-sts-card/50 border border-transparent"
      }`}
    >
      <span className={`w-5 h-5 rounded text-[10px] font-bold flex items-center justify-center ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(floor.type)}`}>
        {icon}
      </span>
      <span className="font-mono text-sts-text w-5">{floor.floor}</span>
      <span className="text-sts-text truncate flex-1">
        {floor.room_id || floor.type}
      </span>
      {isLive && combat?.result === "in_progress" && (
        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
      )}
      {combat && combat.result !== "in_progress" && (
        <span className={`text-[10px] font-bold ${combat.result === "win" ? "text-sts-green" : "text-sts-red"}`}>
          {combat.result === "win" ? "W" : "L"}
        </span>
      )}
    </button>
  );
}
