import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { RunData, MapPoint, FloorPlayerStats } from "../utils/types";
import {
  formatGameId,
  formatDuration,
  formatDate,
  roomTypeColor,
  roomTypeBg,
} from "../utils/format";

export default function RunDetail() {
  const { filename } = useParams<{ filename: string }>();
  const [run, setRun] = useState<RunData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filename) return;
    fetch(`/api/runs/${filename}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setRun(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [filename]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center text-sts-text-dim py-12">
          Loading run...
        </div>
      </div>
    );
  }
  if (error || !run) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center text-sts-red py-12">
          Error: {error || "Run not found"}
        </div>
      </div>
    );
  }

  const characters = run.players.map((p) => formatGameId(p.character)).join(", ");
  const killedBy =
    run.killed_by_encounter !== "NONE.NONE"
      ? formatGameId(run.killed_by_encounter)
      : run.killed_by_event !== "NONE.NONE"
      ? formatGameId(run.killed_by_event)
      : "";

  // Flatten floors across acts for the timeline
  const allFloors: { actIdx: number; floorIdx: number; point: MapPoint }[] = [];
  run.map_point_history.forEach((act, actIdx) => {
    act.forEach((point, floorIdx) => {
      allFloors.push({ actIdx, floorIdx, point });
    });
  });

  // Build HP chart data from first player's perspective
  const hpData = allFloors.map((f, i) => {
    const ps = f.point.player_stats[0];
    return {
      floor: i + 1,
      hp: ps?.current_hp ?? 0,
      maxHp: ps?.max_hp ?? 0,
      type: f.point.map_point_type,
    };
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Back link */}
      <Link
        to="/history"
        className="text-sm text-sts-gold hover:text-sts-gold-light mb-4 inline-block"
      >
        &larr; Back to Run History
      </Link>

      {/* Run header */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-sts-gold">{characters}</h1>
            <p className="text-sm text-sts-text-dim mt-1">
              Seed: {run.seed} | {formatDate(run.start_time)} |{" "}
              {formatDuration(run.run_time)} | A{run.ascension} |{" "}
              {run.game_mode}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {run.win ? (
              <span className="text-2xl font-bold text-sts-green">
                VICTORY
              </span>
            ) : run.was_abandoned ? (
              <span className="text-2xl font-bold text-sts-text-dim">
                ABANDONED
              </span>
            ) : (
              <div>
                <span className="text-2xl font-bold text-sts-red">DEFEAT</span>
                {killedBy && (
                  <p className="text-sm text-sts-text-dim mt-1">
                    Killed by: {killedBy}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* HP chart */}
      {hpData.length > 0 && (
        <div className="bg-sts-surface border border-sts-border rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-sts-text-dim mb-3">
            HP Over Run
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hpData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3a5c" />
                <XAxis
                  dataKey="floor"
                  stroke="#94a3b8"
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e2d4a",
                    border: "1px solid #2a3a5c",
                    borderRadius: "8px",
                    color: "#e2e8f0",
                  }}
                  formatter={(value: number, name: string) => [
                    value,
                    name === "hp" ? "HP" : "Max HP",
                  ]}
                />
                <Bar dataKey="maxHp" fill="#2a3a5c" name="Max HP" radius={[2, 2, 0, 0]} />
                <Bar dataKey="hp" fill="#ef4444" name="HP" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Floor-by-floor timeline */}
      <h3 className="text-lg font-semibold text-sts-gold mb-4">
        Floor-by-Floor
      </h3>
      <div className="space-y-2">
        {allFloors.map((f, i) => (
          <FloorRow
            key={i}
            floorNum={i + 1}
            point={f.point}
            actIdx={f.actIdx}
          />
        ))}
      </div>

      {/* Final deck, relics, potions */}
      <div className="mt-8 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {run.players.map((player, pi) => (
          <React.Fragment key={pi}>
            {/* Deck */}
            <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-sts-gold mb-3">
                Final Deck ({player.deck.length} cards)
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {player.deck.map((card, ci) => (
                  <span
                    key={ci}
                    className="px-2 py-1 bg-sts-card rounded text-xs text-sts-gold-light border border-sts-border/50"
                    title={`Added floor ${card.floor_added_to_deck || "?"}, upgrade ${card.current_upgrade_level || 0}`}
                  >
                    {formatGameId(card.id)}
                    {(card.current_upgrade_level ?? 0) > 0 && (
                      <span className="text-sts-green ml-0.5">
                        +{card.current_upgrade_level}
                      </span>
                    )}
                  </span>
                ))}
              </div>
            </div>

            {/* Relics */}
            <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-sts-gold mb-3">
                Relics ({player.relics.length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {player.relics.map((relic, ri) => (
                  <span
                    key={ri}
                    className="px-2 py-1 bg-sts-card rounded text-xs text-sts-amber border border-sts-border/50"
                  >
                    {formatGameId(relic.id)}
                  </span>
                ))}
              </div>
            </div>

            {/* Potions */}
            <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-sts-gold mb-3">
                Potions ({player.potions.length}/{player.max_potion_slot_count})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {player.potions.length > 0 ? (
                  player.potions.map((potion, poi) => (
                    <span
                      key={poi}
                      className="px-2 py-1 bg-sts-card rounded text-xs text-sts-purple border border-sts-border/50"
                    >
                      {formatGameId(potion.id)}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-sts-text-dim">No potions</span>
                )}
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FloorRow sub-component
// ---------------------------------------------------------------------------

function FloorRow({
  floorNum,
  point,
  actIdx,
}: {
  floorNum: number;
  point: MapPoint;
  actIdx: number;
}) {
  const room = point.rooms[0];
  const ps = point.player_stats[0] as FloorPlayerStats | undefined;
  const roomType = room?.room_type || point.map_point_type;
  const roomName = room?.model_id
    ? formatGameId(room.model_id)
    : point.map_point_type;

  // Cards gained this floor
  const cardsGained = ps?.cards_gained?.map((c) => formatGameId(c.id)) || [];
  const relicsGained =
    ps?.relic_choices
      ?.filter((r) => r.was_picked)
      .map((r) => formatGameId(r.choice)) || [];
  const potionsGained =
    ps?.potion_choices
      ?.filter((p) => p.was_picked)
      .map((p) => formatGameId(p.choice)) || [];

  const hpPct = ps && ps.max_hp > 0 ? (ps.current_hp / ps.max_hp) * 100 : 0;
  const hpCritical = hpPct < 25;

  return (
    <div
      className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border border-sts-border/30 ${roomTypeBg(
        roomType
      )}`}
    >
      {/* Floor number */}
      <span className="w-8 text-center text-sm font-mono text-sts-text-dim">
        {floorNum}
      </span>

      {/* Room type badge */}
      <span
        className={`w-16 text-center text-xs font-semibold uppercase ${roomTypeColor(
          roomType
        )}`}
      >
        {roomType}
      </span>

      {/* Room name */}
      <span className="w-48 text-sm truncate" title={roomName}>
        {roomName}
      </span>

      {/* HP bar */}
      {ps && (
        <div className="flex items-center gap-2 w-40">
          <div className="flex-1 h-3 bg-sts-bg rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                hpCritical ? "bg-sts-red hp-critical" : "bg-sts-red"
              }`}
              style={{ width: `${hpPct}%` }}
            />
          </div>
          <span className="text-xs font-mono text-sts-text-dim w-16 text-right">
            {ps.current_hp}/{ps.max_hp}
          </span>
        </div>
      )}

      {/* Damage taken */}
      {ps && ps.damage_taken > 0 && (
        <span className="text-xs text-orange-400 font-mono">
          -{ps.damage_taken}
        </span>
      )}

      {/* Gold */}
      {ps && (
        <span className="text-xs text-sts-gold font-mono w-12 text-right">
          {ps.current_gold}g
        </span>
      )}

      {/* Gains */}
      <div className="flex-1 flex flex-wrap gap-1 ml-2">
        {cardsGained.map((c, i) => (
          <span
            key={`card-${i}`}
            className="px-1.5 py-0.5 bg-sts-card/50 rounded text-xs text-sts-gold-light"
          >
            {c}
          </span>
        ))}
        {relicsGained.map((r, i) => (
          <span
            key={`relic-${i}`}
            className="px-1.5 py-0.5 bg-amber-900/30 rounded text-xs text-sts-amber"
          >
            {r}
          </span>
        ))}
        {potionsGained.map((p, i) => (
          <span
            key={`potion-${i}`}
            className="px-1.5 py-0.5 bg-purple-900/30 rounded text-xs text-sts-purple"
          >
            {p}
          </span>
        ))}
      </div>
    </div>
  );
}
