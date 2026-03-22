import React, { useEffect, useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ProgressData, CharacterStat, CardStat, EncounterStat } from "../utils/types";
import { formatGameId, formatDuration } from "../utils/format";

const CHARACTER_COLORS: Record<string, string> = {
  "CHARACTER.IRONCLAD": "#ef4444",
  "CHARACTER.SILENT": "#22c55e",
  "CHARACTER.DEFECT": "#3b82f6",
  "CHARACTER.NECROBINDER": "#a855f7",
  "CHARACTER.REGENT": "#f59e0b",
};

function getCharColor(id: string): string {
  return CHARACTER_COLORS[id] || "#94a3b8";
}

export default function Stats() {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/progress")
      .then((r) => r.json())
      .then((res) => {
        if (res.status === "ok" && res.data) {
          setProgress(res.data);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center text-sts-text-dim py-12">
          Loading stats...
        </div>
      </div>
    );
  }
  if (error || !progress) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center text-sts-red py-12">
          {error ? `Error: ${error}` : "No progress data available"}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-sts-gold mb-6">
        Stats Overview
      </h1>

      {/* Global stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <GlobalStat
          label="Total Playtime"
          value={formatDuration(progress.total_playtime)}
        />
        <GlobalStat
          label="Floors Climbed"
          value={progress.floors_climbed.toLocaleString()}
        />
        <GlobalStat
          label="Architect Damage"
          value={progress.architect_damage.toLocaleString()}
        />
        <GlobalStat
          label="Total Runs"
          value={progress.character_stats
            .reduce((sum, c) => sum + c.total_wins + c.total_losses, 0)
            .toLocaleString()}
        />
      </div>

      {/* Character stats */}
      <CharacterStatsSection stats={progress.character_stats} />

      {/* Card stats */}
      <CardStatsSection stats={progress.card_stats} />

      {/* Encounter stats */}
      <EncounterStatsSection stats={progress.encounter_stats} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function GlobalStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-sts-surface border border-sts-border rounded-lg p-4 text-center">
      <div className="text-xl font-bold text-sts-gold">{value}</div>
      <div className="text-xs text-sts-text-dim mt-1">{label}</div>
    </div>
  );
}

function formatMinutes(seconds: number): string {
  if (seconds <= 0) return "-";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatHours(seconds: number): string {
  if (seconds <= 0) return "0h";
  const h = (seconds / 3600).toFixed(1);
  return `${h}h`;
}

function CharacterStatsSection({ stats }: { stats: CharacterStat[] }) {
  const tableData = useMemo(() => {
    return stats
      .map((c) => {
        const total = c.total_wins + c.total_losses;
        return {
          ...c,
          name: formatGameId(c.id),
          total,
          winRate: total > 0 ? (c.total_wins / total) * 100 : 0,
        };
      })
      .sort((a, b) => b.winRate - a.winRate);
  }, [stats]);

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-sts-gold mb-4">
        Character Stats
      </h2>

      <div className="bg-sts-surface border border-sts-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-sts-border bg-sts-card/50 text-sts-text-dim text-left">
                <th className="py-2 px-4 font-medium">Character</th>
                <th className="py-2 px-4 font-medium text-right">W / L</th>
                <th className="py-2 px-4 font-medium text-right">Win Rate</th>
                <th className="py-2 px-4 font-medium text-right">Best Streak</th>
                <th className="py-2 px-4 font-medium text-right">Max Ascension</th>
                <th className="py-2 px-4 font-medium text-right">Fastest Win</th>
                <th className="py-2 px-4 font-medium text-right">Playtime</th>
              </tr>
            </thead>
            <tbody>
              {tableData.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-sts-border/50 hover:bg-sts-card/30"
                >
                  <td
                    className="py-2 px-4 font-bold"
                    style={{ color: getCharColor(c.id) }}
                  >
                    {c.name}
                  </td>
                  <td className="py-2 px-4 text-right font-mono">
                    <span className="text-sts-green">{c.total_wins}</span>
                    <span className="text-sts-text-dim"> / </span>
                    <span className="text-sts-red">{c.total_losses}</span>
                  </td>
                  <td className="py-2 px-4 text-right font-mono font-bold">
                    <span
                      className={
                        c.winRate >= 60
                          ? "text-sts-green"
                          : c.winRate < 40
                          ? "text-sts-red"
                          : "text-sts-text"
                      }
                    >
                      {c.total > 0 ? `${Math.round(c.winRate)}%` : "-"}
                    </span>
                  </td>
                  <td className="py-2 px-4 text-right font-mono text-sts-amber">
                    {c.best_win_streak}
                  </td>
                  <td className="py-2 px-4 text-right font-mono">
                    {c.max_ascension}
                  </td>
                  <td className="py-2 px-4 text-right font-mono">
                    {formatMinutes(c.fastest_win_time)}
                  </td>
                  <td className="py-2 px-4 text-right font-mono text-sts-text-dim">
                    {formatHours(c.playtime)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CardStatsSection({ stats }: { stats: CardStat[] }) {
  const [sortBy, setSortBy] = useState<"picked" | "pickRate" | "winRate">("picked");
  const [minOffers, setMinOffers] = useState(3);

  const sorted = useMemo(() => {
    const withRates = stats
      .filter((c) => c.times_picked > 0 || c.times_won > 0 || c.times_lost > 0)
      .map((c) => {
        const total = c.times_won + c.times_lost;
        const offers = c.times_picked + c.times_skipped;
        return {
          ...c,
          offers,
          pickRate:
            offers > 0
              ? Math.round(
                  (c.times_picked / offers) * 100
                )
              : 0,
          winRate: total > 0 ? Math.round((c.times_won / total) * 100) : 0,
          total,
        };
      })
      .filter((c) => c.offers >= minOffers);

    if (sortBy === "picked") {
      withRates.sort((a, b) => b.times_picked - a.times_picked);
    } else if (sortBy === "pickRate") {
      withRates.sort((a, b) => b.pickRate - a.pickRate || b.offers - a.offers);
    } else {
      withRates.sort((a, b) => {
        // Sort by win rate, but require at least 3 games
        const aEligible = a.total >= 3;
        const bEligible = b.total >= 3;
        if (aEligible !== bEligible) return bEligible ? 1 : -1;
        return b.winRate - a.winRate;
      });
    }

    return withRates.slice(0, 30);
  }, [stats, sortBy, minOffers]);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-sts-gold">
          Card Stats (Top 30)
        </h2>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-xs text-sts-text-dim whitespace-nowrap">
              Min Offers:
            </label>
            <input
              type="number"
              min={0}
              max={100}
              value={minOffers}
              onChange={(e) => setMinOffers(Math.max(0, parseInt(e.target.value) || 0))}
              className="w-16 px-2 py-1 rounded text-xs font-mono bg-sts-card border border-sts-border text-sts-text focus:outline-none focus:border-sts-gold"
            />
          </div>
          <div className="flex gap-2">
            <button
              className={`px-3 py-1 rounded text-xs font-medium ${
                sortBy === "picked"
                  ? "bg-sts-gold text-sts-bg"
                  : "bg-sts-card text-sts-text-dim hover:text-sts-text"
              }`}
              onClick={() => setSortBy("picked")}
            >
              By Pick Count
            </button>
            <button
              className={`px-3 py-1 rounded text-xs font-medium ${
                sortBy === "pickRate"
                  ? "bg-sts-gold text-sts-bg"
                  : "bg-sts-card text-sts-text-dim hover:text-sts-text"
              }`}
              onClick={() => setSortBy("pickRate")}
            >
              By Pick %
            </button>
            <button
              className={`px-3 py-1 rounded text-xs font-medium ${
                sortBy === "winRate"
                  ? "bg-sts-gold text-sts-bg"
                  : "bg-sts-card text-sts-text-dim hover:text-sts-text"
              }`}
              onClick={() => setSortBy("winRate")}
            >
              By Win Rate
            </button>
          </div>
        </div>
      </div>
      <div className="bg-sts-surface border border-sts-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-sts-border bg-sts-card/50 text-sts-text-dim text-left">
                <th className="py-2 px-4 font-medium">Card</th>
                <th className="py-2 px-4 font-medium text-right">Picked</th>
                <th className="py-2 px-4 font-medium text-right">Skipped</th>
                <th className="py-2 px-4 font-medium text-right">Pick Rate</th>
                <th className="py-2 px-4 font-medium text-right">Wins</th>
                <th className="py-2 px-4 font-medium text-right">Losses</th>
                <th className="py-2 px-4 font-medium text-right">Win Rate</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((card) => (
                <tr
                  key={card.id}
                  className="border-b border-sts-border/50 hover:bg-sts-card/30"
                >
                  <td className="py-2 px-4 text-sts-gold-light font-medium">
                    {formatGameId(card.id)}
                  </td>
                  <td className="py-2 px-4 text-right font-mono">
                    {card.times_picked}
                  </td>
                  <td className="py-2 px-4 text-right font-mono text-sts-text-dim">
                    {card.times_skipped}
                  </td>
                  <td className="py-2 px-4 text-right font-mono">
                    {card.pickRate}%
                  </td>
                  <td className="py-2 px-4 text-right font-mono text-sts-green">
                    {card.times_won}
                  </td>
                  <td className="py-2 px-4 text-right font-mono text-sts-red">
                    {card.times_lost}
                  </td>
                  <td className="py-2 px-4 text-right font-mono font-bold">
                    <span
                      className={
                        card.winRate >= 60
                          ? "text-sts-green"
                          : card.winRate < 40
                          ? "text-sts-red"
                          : "text-sts-text"
                      }
                    >
                      {card.total >= 3 ? `${card.winRate}%` : "-"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EncounterStatsSection({ stats }: { stats: EncounterStat[] }) {
  // Find hardest encounters (highest loss rate across all characters)
  const encounterData = useMemo(() => {
    return stats
      .map((e) => {
        const totalWins = e.fight_stats.reduce((s, f) => s + f.wins, 0);
        const totalLosses = e.fight_stats.reduce((s, f) => s + f.losses, 0);
        const total = totalWins + totalLosses;
        return {
          name: formatGameId(e.encounter_id),
          id: e.encounter_id,
          wins: totalWins,
          losses: totalLosses,
          total,
          lossRate: total > 0 ? Math.round((totalLosses / total) * 100) : 0,
        };
      })
      .filter((e) => e.total >= 3)
      .sort((a, b) => b.lossRate - a.lossRate)
      .slice(0, 20);
  }, [stats]);

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-sts-gold mb-4">
        Hardest Encounters (Top 20)
      </h2>
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={encounterData}
              layout="vertical"
              margin={{ top: 5, right: 10, left: 120, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3a5c" />
              <XAxis
                type="number"
                stroke="#94a3b8"
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#94a3b8"
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                width={110}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e2d4a",
                  border: "1px solid #2a3a5c",
                  borderRadius: "8px",
                  color: "#e2e8f0",
                }}
                formatter={(value: number, name: string) => [
                  `${value}%`,
                  name === "lossRate" ? "Loss Rate" : name,
                ]}
              />
              <Bar dataKey="lossRate" fill="#ef4444" name="Loss Rate" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

