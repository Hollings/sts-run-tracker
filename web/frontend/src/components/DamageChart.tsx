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

interface TurnData {
  turn: number;
  damage: number;
  block: number;
  cards: number;
}

interface Props {
  damagePerTurn: number[];
  blockPerTurn: number[];
  cardsPerTurn: number[];
}

export default function DamageChart({
  damagePerTurn,
  blockPerTurn,
  cardsPerTurn,
}: Props) {
  const data: TurnData[] = damagePerTurn.map((dmg, i) => ({
    turn: i + 1,
    damage: dmg,
    block: blockPerTurn[i] || 0,
    cards: cardsPerTurn[i] || 0,
  }));

  if (data.length === 0) {
    return (
      <div className="text-sts-text-dim text-sm text-center py-4">
        No turn data available
      </div>
    );
  }

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#2a3a5c" />
          <XAxis
            dataKey="turn"
            stroke="#94a3b8"
            tick={{ fontSize: 12, fill: "#94a3b8" }}
            label={{
              value: "Turn",
              position: "insideBottom",
              offset: -2,
              fill: "#94a3b8",
              fontSize: 12,
            }}
          />
          <YAxis
            stroke="#94a3b8"
            tick={{ fontSize: 12, fill: "#94a3b8" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e2d4a",
              border: "1px solid #2a3a5c",
              borderRadius: "8px",
              color: "#e2e8f0",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
          />
          <Bar dataKey="damage" fill="#ef4444" name="Damage" radius={[2, 2, 0, 0]} />
          <Bar dataKey="block" fill="#3b82f6" name="Block" radius={[2, 2, 0, 0]} />
          <Bar dataKey="cards" fill="#d4a843" name="Cards" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
