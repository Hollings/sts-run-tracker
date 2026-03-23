import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PlayerCombatStats } from "../utils/types";

interface Props {
  /** All players' combat stats for this fight */
  players: Record<string, PlayerCombatStats>;
}

export default function DamageChart({ players }: Props) {
  const entries = Object.values(players);
  if (entries.length === 0) return null;

  // Find the max turn count across all players
  const maxTurns = Math.max(
    ...entries.map((s) => Math.max(
      s.damage_per_turn.length,
      s.block_per_turn.length,
      s.damage_taken_per_turn?.length ?? 0,
    )),
    0,
  );

  if (maxTurns === 0) {
    return (
      <div className="text-sts-text text-sm text-center py-4">
        No turn data available
      </div>
    );
  }

  // Aggregate per-turn: party damage dealt, party block, enemy damage (= party damage taken)
  const data = Array.from({ length: maxTurns }, (_, i) => {
    let partyDamage = 0;
    let partyBlock = 0;
    let enemyDamage = 0;
    for (const s of entries) {
      partyDamage += s.damage_per_turn[i] ?? 0;
      partyBlock += s.block_per_turn[i] ?? 0;
      enemyDamage += (s.damage_taken_per_turn?.[i] ?? 0) + (s.damage_blocked_per_turn?.[i] ?? 0);
    }
    return {
      turn: i + 1,
      "Party Damage": partyDamage,
      "Party Block": partyBlock,
      "Enemy Damage": enemyDamage,
    };
  });

  return (
    <div className="w-full h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a5a6b" />
          <XAxis
            dataKey="turn"
            stroke="#776754"
            tick={{ fontSize: 11, fill: "#776754" }}
            label={{ value: "Turn", position: "insideBottom", offset: -2, fill: "#776754", fontSize: 11 }}
          />
          <YAxis stroke="#776754" tick={{ fontSize: 11, fill: "#776754" }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#183749",
              border: "1px solid #2a5a6b",
              borderRadius: "8px",
              color: "#F2F0C4",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: "#776754" }} />
          <Bar dataKey="Party Damage" fill="#e85550" radius={[2, 2, 0, 0]} />
          <Bar dataKey="Party Block" fill="#4a8aaf" radius={[2, 2, 0, 0]} />
          <Bar dataKey="Enemy Damage" fill="#d4943a" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
