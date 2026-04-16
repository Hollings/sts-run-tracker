import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { MergedLiveData } from "../utils/types";
import { formatGameId } from "../utils/format";
import {
  averageDamagePerTurn,
  getPlayerIds,
  getPlayerCharacter,
  playerColor,
} from "../utils/runAggregates";

interface Props {
  data: MergedLiveData;
}

function TurnTooltip({ active, payload, label, pids, data }: any) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;

  return (
    <div
      style={{
        backgroundColor: "#183749",
        border: "1px solid #2a5a6b",
        borderRadius: 8,
        padding: "8px 12px",
        color: "#F2F0C4",
        fontSize: 12,
      }}
    >
      <div style={{ marginBottom: 4, fontWeight: 600 }}>Turn {label}</div>
      {(pids as string[]).map((pid: string, i: number) => {
        const val = point?.[pid] ?? 0;
        const n = point?.[`${pid}_n`] ?? 0;
        return (
          <div key={pid} style={{ color: playerColor(i) }}>
            {formatGameId(getPlayerCharacter(data, pid))}: {val} avg
            <span style={{ color: "#776754", marginLeft: 6 }}>
              ({n} combat{n !== 1 ? "s" : ""})
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function AvgDamagePerTurnChart({ data }: Props) {
  const chartData = averageDamagePerTurn(data);
  const pids = getPlayerIds(data);
  const totalCombats = data.combats.length;

  if (chartData.length === 0) {
    return (
      <div className="text-sts-text text-sm text-center py-4">
        No combat data yet
      </div>
    );
  }

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#2a5a6b" />
          <XAxis
            dataKey="turn"
            stroke="#776754"
            tick={{ fontSize: 11, fill: "#776754" }}
            label={{
              value: "Turn",
              position: "insideBottom",
              offset: -2,
              fill: "#776754",
              fontSize: 11,
            }}
          />
          <YAxis
            stroke="#776754"
            tick={{ fontSize: 11, fill: "#776754" }}
          />
          <Tooltip
            content={<TurnTooltip pids={pids} data={data} />}
          />
          {pids.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#776754" }}
              formatter={(value: string) =>
                formatGameId(getPlayerCharacter(data, value))
              }
            />
          )}
          {pids.map((pid, i) => (
            <Line
              key={pid}
              type="monotone"
              dataKey={pid}
              name={pid}
              stroke={playerColor(i)}
              strokeWidth={2}
              dot={(props: any) => {
                const n = props.payload?.[`${pid}_n`] ?? 0;
                const dimmed = n <= 1 && totalCombats > 2;
                return (
                  <circle
                    cx={props.cx}
                    cy={props.cy}
                    r={3}
                    fill={playerColor(i)}
                    opacity={dimmed ? 0.3 : 1}
                  />
                );
              }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
