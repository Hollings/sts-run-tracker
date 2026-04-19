import React, { useState, useEffect } from "react";
import type { MergedLiveData, Floor } from "../utils/types";
import { formatGameId } from "../utils/format";
import { FloorDetailView } from "../components/FloorDetail";
import { TopStat, RunTotalCard, SidebarFloorItem } from "../components/RunSidebar";
import RunSummary from "../components/RunSummary";

interface Props {
  data: MergedLiveData | null;
}

export default function LiveRun({ data }: Props) {
  const [selectedFloor, setSelectedFloor] = useState<number | null>(null);
  const [showSummary, setShowSummary] = useState(false);

  const isRunComplete = data
    ? (() => {
        const last = data.floors[data.floors.length - 1];
        return last?.type === "boss" && last?.combat?.result === "win";
      })()
    : false;

  useEffect(() => {
    if (data && data.floors.length > 0 && selectedFloor === null) {
      setSelectedFloor(data.floors[data.floors.length - 1].floor);
    }
  }, [data?.floors.length]);

  useEffect(() => {
    if (data && data.floors.length > 0) {
      const latest = data.floors[data.floors.length - 1];
      if (latest.combat?.result === "in_progress") {
        setSelectedFloor(latest.floor);
        setShowSummary(false);
      }
    }
  }, [data?.combats.length]);

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
  const activeFloor =
    floors.find((f) => f.floor === selectedFloor) || latestFloor;
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
            <TopStat
              label="Combats"
              value={run_totals?.total_combats ?? combats.length}
            />
            <TopStat label="Damage" value={totalDamage} color="text-sts-red" />
            <TopStat
              label="Taken"
              value={totalTaken}
              color="text-orange-400"
            />
          </div>
        </div>
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 140px)" }}>
        {/* Left 2/3 - Detail view */}
        <div className="flex-1 min-w-0 flex flex-col">
          {showSummary ? (
            <RunSummary
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
            <h3 className="text-sm font-semibold text-sts-gold mb-2">
              Run Totals
            </h3>
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
