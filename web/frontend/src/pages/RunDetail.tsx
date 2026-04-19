import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { HistoricalRunData, Floor } from "../utils/types";
import { formatGameId, formatDuration, formatDate } from "../utils/format";
import { FloorDetailView } from "../components/FloorDetail";
import {
  TopStat,
  RunTotalCard,
  SidebarFloorItem,
} from "../components/RunSidebar";
import RunSummary from "../components/RunSummary";

export default function RunDetail() {
  const { filename } = useParams<{ filename: string }>();
  const [run, setRun] = useState<HistoricalRunData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<number | null>(null);
  const [showSummary, setShowSummary] = useState(false);

  useEffect(() => {
    if (!filename) return;
    fetch(`/api/runs/${filename}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: HistoricalRunData) => {
        setRun(data);
        setLoading(false);
        if (data.floors.length > 0) {
          setSelectedFloor(data.floors[data.floors.length - 1].floor);
        }
        if (data.historical?.win && data.combats.length > 0) {
          setShowSummary(true);
        }
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [filename]);

  if (loading) {
    return (
      <div className="max-w-[1400px] mx-auto px-4 py-6">
        <div className="text-center text-sts-text py-12">Loading run...</div>
      </div>
    );
  }
  if (error || !run) {
    return (
      <div className="max-w-[1400px] mx-auto px-4 py-6">
        <div className="text-center text-sts-red py-12">
          Error: {error || "Run not found"}
        </div>
      </div>
    );
  }

  const hist = run.historical ?? {
    win: false,
    was_abandoned: false,
    run_time: 0,
    start_time: 0,
    killed_by_encounter: "",
    killed_by_event: "",
    game_mode: "",
    has_tracker_data: false,
    players_final: [],
  };
  const { floors, combats, run_info, run_totals } = run;
  const activeFloor = floors.find((f) => f.floor === selectedFloor) || floors[floors.length - 1];
  const playerEntries = run_totals?.players
    ? Object.entries(run_totals.players)
    : [];

  let totalDamage = 0;
  let totalTaken = 0;
  for (const [, pt] of playerEntries) {
    totalDamage += pt.damage_dealt;
    totalTaken += pt.damage_taken;
  }

  const characters =
    run_info?.players?.map((p) => formatGameId(p.character)).join(" & ") || "";
  const killedBy =
    hist.killed_by_encounter && hist.killed_by_encounter !== "NONE.NONE"
      ? formatGameId(hist.killed_by_encounter)
      : hist.killed_by_event && hist.killed_by_event !== "NONE.NONE"
        ? formatGameId(hist.killed_by_event)
        : "";

  const resultLabel = hist.win
    ? "VICTORY"
    : hist.was_abandoned
      ? "ABANDONED"
      : "DEFEAT";
  const resultColor = hist.win
    ? "text-sts-green"
    : hist.was_abandoned
      ? "text-sts-text"
      : "text-sts-red";

  const subtitle = [
    `${floors.length} floors`,
    combats.length > 0 ? `${combats.length} combats` : null,
    formatDuration(hist.run_time),
    !hist.win && killedBy ? `Killed by ${killedBy}` : null,
  ]
    .filter(Boolean)
    .join(" | ");

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">
      {/* Top bar */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-3 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/history"
              className="text-sm text-sts-gold hover:text-sts-gold-light"
            >
              &larr;
            </Link>
            <div>
              <span className="text-lg font-bold text-sts-gold">
                {run_info?.seed || "Historical Run"}
              </span>
              <span className="text-sm text-sts-text ml-3">
                {run_info?.ascension != null && run_info.ascension > 0
                  ? `A${run_info.ascension} `
                  : ""}
                {characters}
              </span>
              <span className="text-xs text-sts-text ml-3">
                {formatDate(hist.start_time)}
              </span>
            </div>
          </div>
          <div className="flex gap-6 text-center">
            <TopStat label="Floors" value={floors.length} />
            <TopStat
              label="Combats"
              value={run_totals?.total_combats ?? combats.length}
            />
            <TopStat label="Damage" value={totalDamage} color="text-sts-red" />
            <TopStat label="Time" value={formatDuration(hist.run_time)} />
            <div>
              <div className={`text-xl font-bold ${resultColor}`}>
                {resultLabel}
              </div>
              <div className="text-[10px] text-sts-text uppercase tracking-wide">
                Result
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 140px)" }}>
        {/* Left 2/3 - Detail view */}
        <div className="flex-1 min-w-0 flex flex-col">
          {showSummary ? (
            <div className="flex flex-col h-full gap-4 overflow-y-auto">
              <RunSummary
                data={run}
                resultLabel={resultLabel}
                resultColor={resultColor}
                subtitle={subtitle}
                onClose={() => setShowSummary(false)}
              />

              {/* Final deck, relics, potions */}
              {hist.players_final?.length > 0 && (
                <FinalState players={hist.players_final} />
              )}
            </div>
          ) : activeFloor ? (
            <FloorDetailView
              floor={activeFloor}
              isLive={false}
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
              <p className="text-xs text-sts-text">
                {hist.has_tracker_data
                  ? "No combat data."
                  : "No tracker data for this run."}
              </p>
            ) : (
              <div className="space-y-2">
                {playerEntries.map(([pid, pt]) => (
                  <RunTotalCard key={pid} player={pt} />
                ))}
              </div>
            )}
          </div>

          {/* Summary button */}
          <button
            onClick={() => setShowSummary(!showSummary)}
            className={`w-full py-2.5 rounded-lg text-sm font-bold shrink-0 ${
              showSummary
                ? "bg-sts-gold/20 text-sts-gold border border-sts-gold/30"
                : `${hist.win ? "bg-sts-green/20 text-sts-green border-sts-green/30" : "bg-sts-surface text-sts-text border-sts-border"} border hover:opacity-80`
            }`}
          >
            {showSummary
              ? "View Floor Details"
              : `${resultLabel} - View Summary`}
          </button>

          {/* Floor list */}
          <div className="bg-sts-surface border border-sts-border rounded-lg flex-1 min-h-0 flex flex-col">
            <h3 className="text-sm font-semibold text-sts-gold p-3 pb-2 shrink-0">
              Floors
            </h3>
            <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-1">
              {[...floors].reverse().map((floor) => (
                <SidebarFloorItem
                  key={floor.floor}
                  floor={floor}
                  isLive={false}
                  isSelected={selectedFloor === floor.floor && !showSummary}
                  onClick={() => {
                    setSelectedFloor(floor.floor);
                    setShowSummary(false);
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FinalState({
  players,
}: {
  players: HistoricalRunData["historical"]["players_final"];
}) {
  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 shrink-0 pb-4">
      {players.map((player, pi) => (
        <React.Fragment key={pi}>
          {/* Deck */}
          <div className="bg-sts-surface border border-sts-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-sts-gold mb-3">
              {formatGameId(player.character)} - Deck ({player.deck.length})
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {player.deck.map((card, ci) => (
                <span
                  key={ci}
                  className="px-2 py-1 bg-sts-card rounded text-xs text-sts-gold-light border border-sts-border/50"
                  title={`Added floor ${card.floor_added_to_deck || "?"}`}
                >
                  {card.id}
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
                  {relic.id}
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
                    {potion.id}
                  </span>
                ))
              ) : (
                <span className="text-xs text-sts-text">No potions</span>
              )}
            </div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}
