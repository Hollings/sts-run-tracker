import React from "react";
import type { Floor, PlayerRunTotals } from "../utils/types";
import {
  formatGameId,
  FLOOR_TYPE_ICONS,
  floorTypeBgColor,
  floorTypeTextColor,
} from "../utils/format";

export function TopStat({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div>
      <div className={`text-xl font-bold ${color || "text-sts-text"}`}>
        {value}
      </div>
      <div className="text-[10px] text-sts-text uppercase tracking-wide">
        {label}
      </div>
    </div>
  );
}

export function RunTotalCard({ player }: { player: PlayerRunTotals }) {
  return (
    <div className="bg-sts-card rounded-lg p-2.5 border border-sts-border/30">
      <div className="text-xs font-semibold text-sts-gold-light mb-1.5">
        {formatGameId(player.character)}
      </div>
      <div className="grid grid-cols-3 gap-1 text-center text-xs">
        <div>
          <div className="text-sts-red font-bold">{player.damage_dealt}</div>
          <div className="text-[10px] text-sts-text">Dealt</div>
        </div>
        <div>
          <div className="text-orange-400 font-bold">
            {player.damage_taken}
          </div>
          <div className="text-[10px] text-sts-text">Taken</div>
        </div>
        <div>
          <div className="text-sts-blue font-bold">{player.block_gained}</div>
          <div className="text-[10px] text-sts-text">Block</div>
        </div>
      </div>
      {player.best_hit && player.best_hit.damage > 0 && (
        <div className="mt-1.5 pt-1.5 border-t border-sts-border/30 text-[10px] text-sts-text">
          Best:{" "}
          <span className="text-sts-amber font-bold">
            {player.best_hit.damage}
          </span>{" "}
          with{" "}
          <span className="text-sts-gold-light">{player.best_hit.card}</span>
        </div>
      )}
    </div>
  );
}

export function SidebarFloorItem({
  floor,
  isLive,
  isSelected,
  onClick,
}: {
  floor: Floor;
  isLive: boolean;
  isSelected: boolean;
  onClick: () => void;
}) {
  const combat = floor.combat;
  const icon = FLOOR_TYPE_ICONS[floor.type] || "?";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-2.5 py-1.5 rounded-md flex items-center gap-2 text-xs ${
        isSelected
          ? "bg-sts-gold/10 border border-sts-gold/30"
          : "hover:bg-sts-card/50 border border-transparent"
      }`}
    >
      <span
        className={`w-5 h-5 rounded text-[10px] font-bold flex items-center justify-center ${floorTypeBgColor(floor.type)} ${floorTypeTextColor(floor.type)}`}
      >
        {icon}
      </span>
      <span className="font-mono text-sts-text w-5">{floor.floor}</span>
      <span className="text-sts-text truncate flex-1">
        {floor.room_id || floor.type}
      </span>
      {isLive && combat?.result === "in_progress" && (
        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
      )}
      {combat && combat.result !== "in_progress" && (
        <span
          className={`text-[10px] font-bold ${combat.result === "win" ? "text-sts-green" : "text-sts-red"}`}
        >
          {combat.result === "win" ? "W" : "L"}
        </span>
      )}
    </button>
  );
}
