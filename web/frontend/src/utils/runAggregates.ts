import type { MergedLiveData } from "./types";

export const PLAYER_COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#a855f7"];

export function playerColor(index: number): string {
  return PLAYER_COLORS[index % PLAYER_COLORS.length];
}

export function getPlayerIds(data: MergedLiveData): string[] {
  if (data.run_totals?.players) {
    return Object.keys(data.run_totals.players);
  }
  if (data.combats.length > 0) {
    return Object.keys(data.combats[0].players);
  }
  return [];
}

export function getPlayerCharacter(
  data: MergedLiveData,
  pid: string,
): string {
  const rt = data.run_totals?.players?.[pid];
  if (rt) return rt.character;
  for (const c of data.combats) {
    if (c.players[pid]) return c.players[pid].character;
  }
  return pid;
}

export interface DamagePerFloorPoint {
  floor: number;
  type: string;
  encounter: string;
  [key: string]: string | number;
}

export function avgTurnDamagePerCombat(
  data: MergedLiveData,
): DamagePerFloorPoint[] {
  const pids = getPlayerIds(data);
  const points: DamagePerFloorPoint[] = [];

  for (const floor of data.floors) {
    if (!floor.combat) continue;
    const turns = floor.combat.total_turns || 1;
    const point: DamagePerFloorPoint = {
      floor: floor.floor,
      type: floor.type,
      encounter: floor.room_id || floor.type,
      turns,
    };
    for (const pid of pids) {
      const stats = floor.combat.players[pid];
      point[pid] = stats ? Math.round(stats.damage_dealt / turns) : 0;
    }
    points.push(point);
  }

  return points;
}

export interface AvgDamagePerTurnPoint {
  turn: number;
  [key: string]: number;
}

export function averageDamagePerTurn(
  data: MergedLiveData,
): AvgDamagePerTurnPoint[] {
  const pids = getPlayerIds(data);
  const combats = data.combats;
  if (combats.length === 0) return [];

  const maxTurns = Math.max(
    ...combats.flatMap((c) =>
      Object.values(c.players).map((p) => p.damage_per_turn.length),
    ),
    0,
  );
  if (maxTurns === 0) return [];

  const points: AvgDamagePerTurnPoint[] = [];
  for (let t = 0; t < maxTurns; t++) {
    const point: AvgDamagePerTurnPoint = { turn: t + 1 };

    for (const pid of pids) {
      let sum = 0;
      let count = 0;
      for (const combat of combats) {
        const stats = combat.players[pid];
        if (stats && stats.damage_per_turn.length > t) {
          sum += stats.damage_per_turn[t];
          count++;
        }
      }
      point[pid] = count > 0 ? Math.round(sum / count) : 0;
      point[`${pid}_n`] = count;
    }

    points.push(point);
  }

  return points;
}
