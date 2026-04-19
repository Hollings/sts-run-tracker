import React from "react";
import type { MergedLiveData } from "../utils/types";
import { formatGameId } from "../utils/format";
import { StatRow } from "./FloorDetail";
import DamagePerFloorChart from "./DamagePerFloorChart";
import AvgDamagePerTurnChart from "./AvgDamagePerTurnChart";

interface Props {
  data: MergedLiveData;
  resultLabel?: string;
  resultColor?: string;
  subtitle?: string;
  onClose?: () => void;
  closeLabel?: string;
}

export default function RunSummary({
  data,
  resultLabel = "VICTORY",
  resultColor = "text-sts-green",
  subtitle,
  onClose,
  closeLabel = "View Floor Details",
}: Props) {
  const { combats, run_totals, floors } = data;
  const playerEntries = run_totals?.players
    ? Object.entries(run_totals.players)
    : [];

  const cardPlays: Record<string, number> = {};
  const cardDamage: Record<
    string,
    { total_damage: number; hits: number; max_hit: number; kills: number }
  > = {};
  for (const c of combats) {
    for (const stats of Object.values(c.players)) {
      for (const play of stats.card_sequence) {
        cardPlays[play.card] = (cardPlays[play.card] || 0) + 1;
      }
      for (const [cardId, cs] of Object.entries(stats.damage_by_card)) {
        if (!cardDamage[cardId]) {
          cardDamage[cardId] = {
            total_damage: 0,
            hits: 0,
            max_hit: 0,
            kills: 0,
          };
        }
        cardDamage[cardId].total_damage += cs.total_damage;
        cardDamage[cardId].hits += cs.hits;
        cardDamage[cardId].max_hit = Math.max(
          cardDamage[cardId].max_hit,
          cs.max_hit,
        );
        cardDamage[cardId].kills += cs.kills;
      }
    }
  }

  const totalPlays = Object.values(cardPlays).reduce((a, b) => a + b, 0);
  const totalPartyDamage = playerEntries.reduce(
    (a, [, p]) => a + p.damage_dealt,
    0,
  );
  const totalPartyTaken = playerEntries.reduce(
    (a, [, p]) => a + p.damage_taken,
    0,
  );
  const totalPartyBlock = playerEntries.reduce(
    (a, [, p]) => a + p.block_gained,
    0,
  );
  const totalKills = playerEntries.reduce((a, [, p]) => a + p.kills, 0);

  const mostPlayed = Object.entries(cardPlays).sort(
    (a, b) => b[1] - a[1],
  )[0];
  const mostDamage = Object.entries(cardDamage)
    .filter(([id]) => id !== "_non_card")
    .sort((a, b) => b[1].total_damage - a[1].total_damage)[0];
  const mostKills = Object.entries(cardDamage)
    .filter(([id]) => id !== "_non_card")
    .sort((a, b) => b[1].kills - a[1].kills)[0];
  const bestHit = playerEntries.reduce(
    (best, [, p]) =>
      p.best_hit && p.best_hit.damage > best.damage
        ? { ...p.best_hit, character: p.character }
        : best,
    { card: "", damage: 0, encounter: "", character: "" },
  );
  const mvp = [...playerEntries].sort(
    (a, b) => b[1].damage_dealt - a[1].damage_dealt,
  )[0];
  const tank = [...playerEntries].sort(
    (a, b) => b[1].damage_taken - a[1].damage_taken,
  )[0];

  const factCards: {
    title: string;
    value: string;
    detail: string;
    color: string;
  }[] = [];

  if (mostPlayed) {
    factCards.push({
      title: "Most Played Card",
      value: formatGameId(mostPlayed[0]),
      detail: `${mostPlayed[1]} plays (${Math.round((mostPlayed[1] / totalPlays) * 100)}% of all cards)`,
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
      {/* Result header */}
      <div
        className={`bg-sts-surface border ${resultColor.includes("green") ? "border-sts-green/30" : resultColor.includes("red") ? "border-sts-red/30" : "border-sts-border"} rounded-lg p-6 text-center shrink-0`}
      >
        <div className={`text-4xl font-black ${resultColor} mb-2`}>
          {resultLabel}
        </div>
        <p className="text-sts-text">
          {subtitle ||
            `${floors.length} floors | ${combats.length} combats | ${totalKills} kills`}
        </p>
        {onClose && (
          <button
            onClick={onClose}
            className="mt-3 px-4 py-1.5 text-xs text-sts-text hover:text-sts-text border border-sts-border rounded hover:bg-sts-card/50"
          >
            {closeLabel}
          </button>
        )}
      </div>

      {/* Party totals */}
      {playerEntries.length > 0 && (
        <div className="bg-sts-surface border border-sts-border rounded-lg p-4 shrink-0">
          <h3 className="text-sm font-semibold text-sts-text mb-3">
            Party Totals
          </h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-sts-red">
                {totalPartyDamage}
              </div>
              <div className="text-xs text-sts-text">Damage Dealt</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-400">
                {totalPartyTaken}
              </div>
              <div className="text-xs text-sts-text">Damage Taken</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-sts-blue">
                {totalPartyBlock}
              </div>
              <div className="text-xs text-sts-text">Block Gained</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-sts-text">
                {totalPlays}
              </div>
              <div className="text-xs text-sts-text">Cards Played</div>
            </div>
          </div>
        </div>
      )}

      {/* Fun fact cards */}
      {factCards.length > 0 && (
        <div className="grid grid-cols-3 gap-3 shrink-0">
          {factCards.map((fact, i) => (
            <div
              key={i}
              className="bg-sts-surface border border-sts-border rounded-lg p-4"
            >
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
      )}

      {/* Per-player breakdown */}
      {playerEntries.length > 0 && (
        <div
          className={`grid gap-3 shrink-0 ${playerEntries.length > 2 ? "grid-cols-3" : playerEntries.length > 1 ? "grid-cols-2" : "grid-cols-1"}`}
        >
          {playerEntries.map(([pid, pt]) => (
            <div
              key={pid}
              className="bg-sts-surface border border-sts-border rounded-lg p-4"
            >
              <h4 className="text-sm font-semibold text-sts-gold mb-2">
                {formatGameId(pt.character)}
              </h4>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs mb-3">
                <StatRow
                  label="Damage"
                  value={pt.damage_dealt}
                  color="text-sts-red"
                />
                <StatRow
                  label="Taken"
                  value={pt.damage_taken}
                  color="text-orange-400"
                />
                <StatRow
                  label="Block"
                  value={pt.block_gained}
                  color="text-sts-blue"
                />
                <StatRow
                  label="Kills"
                  value={pt.kills}
                  color="text-sts-text"
                />
              </div>
              {pt.best_hit && pt.best_hit.damage > 0 && (
                <div className="text-xs border-t border-sts-border/50 pt-2">
                  <span className="text-sts-text">Best: </span>
                  <span className="text-sts-amber font-bold">
                    {pt.best_hit.damage}
                  </span>
                  <span className="text-sts-text"> with </span>
                  <span className="text-sts-gold-light">
                    {pt.best_hit.card}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Run aggregate charts */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4 shrink-0">
        <h3 className="text-sm font-semibold text-sts-gold mb-3">
          Avg Turn Damage per Combat
        </h3>
        <DamagePerFloorChart data={data} />
      </div>

      <div className="bg-sts-surface border border-sts-border rounded-lg p-4 shrink-0">
        <h3 className="text-sm font-semibold text-sts-gold mb-3">
          Average Damage per Turn
        </h3>
        <AvgDamagePerTurnChart data={data} />
      </div>
    </div>
  );
}
