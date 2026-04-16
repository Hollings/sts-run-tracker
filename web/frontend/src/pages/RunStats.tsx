import React from "react";
import type { MergedLiveData } from "../utils/types";
import { formatGameId } from "../utils/format";
import DamagePerFloorChart from "../components/DamagePerFloorChart";
import AvgDamagePerTurnChart from "../components/AvgDamagePerTurnChart";

interface Props {
  data: MergedLiveData | null;
}

export default function RunStats({ data }: Props) {
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

  const characters = data.run_info?.players
    ?.map((p) => formatGameId(p.character))
    .join(" & ");
  const asc = data.run_info?.ascension;
  const combatCount = data.combats.length;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-sts-gold">
              Run Stats
            </h1>
            <p className="text-sm text-sts-text">
              {asc != null && asc > 0 ? `A${asc} ` : ""}
              {characters}
              {combatCount > 0 && (
                <span className="text-sts-gold-dim ml-2">
                  ({combatCount} combat{combatCount !== 1 ? "s" : ""})
                </span>
              )}
            </p>
          </div>
          <div className="text-sm font-mono text-sts-gold-dim">
            {data.run_info?.seed}
          </div>
        </div>
      </div>

      {/* Damage per combat floor */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
        <h2 className="text-sm font-semibold text-sts-gold mb-3">
          Damage per Combat
        </h2>
        <p className="text-xs text-sts-gold-dim mb-2">
          Total damage dealt each combat floor
        </p>
        <DamagePerFloorChart data={data} />
      </div>

      {/* Average damage per turn */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
        <h2 className="text-sm font-semibold text-sts-gold mb-3">
          Average Damage per Turn
        </h2>
        <p className="text-xs text-sts-gold-dim mb-2">
          Mean damage dealt on each turn across all combats
        </p>
        <AvgDamagePerTurnChart data={data} />
      </div>
    </div>
  );
}
