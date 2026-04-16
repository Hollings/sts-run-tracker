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
import { formatGameId, floorTypeHexColor } from "../utils/format";
import {
  avgTurnDamagePerCombat,
  getPlayerIds,
  getPlayerCharacter,
  playerColor,
} from "../utils/runAggregates";

interface Props {
  data: MergedLiveData;
}

function FloorTick({ x, y, payload, chartData }: any) {
  const point = chartData?.find((p: any) => p.floor === payload.value);
  const color = point ? floorTypeHexColor(point.type) : "#776754";
  return (
    <text x={x} y={y + 12} textAnchor="middle" fontSize={11} fill={color}>
      {payload.value}
    </text>
  );
}

function FloorTooltip({ active, payload, label, chartData, pids, data }: any) {
  if (!active || !payload?.length) return null;
  const point = chartData?.find((p: any) => p.floor === label);
  const typeLabel = point?.type ?? "";
  const encounter = point?.encounter ?? "";

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
      <div style={{ marginBottom: 4, fontWeight: 600 }}>
        Floor {label}{" "}
        <span style={{ color: floorTypeHexColor(typeLabel) }}>
          {typeLabel}
        </span>
      </div>
      {encounter && (
        <div style={{ fontSize: 11, color: "#776754", marginBottom: 4 }}>
          {encounter}
        </div>
      )}
      {(pids as string[]).map((pid: string, i: number) => {
        const val = point?.[pid] ?? 0;
        return (
          <div key={pid} style={{ color: playerColor(i) }}>
            {formatGameId(getPlayerCharacter(data, pid))}: {val} avg/turn
          </div>
        );
      })}
      <div style={{ fontSize: 11, color: "#776754", marginTop: 2 }}>
        {point?.turns ?? 0} turn{(point?.turns ?? 0) !== 1 ? "s" : ""}
      </div>
    </div>
  );
}

export default function DamagePerFloorChart({ data }: Props) {
  const chartData = avgTurnDamagePerCombat(data);
  const pids = getPlayerIds(data);

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
            dataKey="floor"
            stroke="#776754"
            tick={<FloorTick chartData={chartData} />}
            label={{
              value: "Floor",
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
            content={
              <FloorTooltip chartData={chartData} pids={pids} data={data} />
            }
          />
          {pids.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#776754" }}
              formatter={(value: string) => formatGameId(getPlayerCharacter(data, value))}
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
              dot={{ r: 3, fill: playerColor(i) }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
