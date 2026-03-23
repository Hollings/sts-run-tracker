import React from "react";
import type { CardDamage } from "../utils/types";
import { formatGameId } from "../utils/format";

interface Props {
  damageByCard: Record<string, CardDamage>;
}

export default function CardStats({ damageByCard }: Props) {
  const entries = Object.entries(damageByCard).sort(
    ([, a], [, b]) => b.total_damage - a.total_damage
  );

  if (entries.length === 0) {
    return (
      <div className="text-sts-text text-sm text-center py-4">
        No card damage data available
      </div>
    );
  }

  const maxDmg = entries[0]?.[1].total_damage || 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-sts-border text-sts-text text-left">
            <th className="py-2 px-3 font-medium">Card</th>
            <th className="py-2 px-3 font-medium text-right">Total Damage</th>
            <th className="py-2 px-3 font-medium text-right">Hits</th>
            <th className="py-2 px-3 font-medium text-right">Max Hit</th>
            <th className="py-2 px-3 font-medium text-right">Kills</th>
            <th className="py-2 px-3 font-medium w-40"></th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([cardId, dmg], idx) => {
            const pct = (dmg.total_damage / maxDmg) * 100;
            const isTopHit =
              dmg.max_hit ===
              Math.max(...entries.map(([, d]) => d.max_hit));
            return (
              <tr
                key={cardId}
                className={`border-b border-sts-border/50 hover:bg-sts-surface/50 ${
                  idx === 0 ? "bg-sts-gold/5" : ""
                }`}
              >
                <td className="py-2 px-3 font-medium text-sts-gold-light">
                  {formatGameId(cardId)}
                </td>
                <td className="py-2 px-3 text-right font-mono">
                  {dmg.total_damage}
                </td>
                <td className="py-2 px-3 text-right font-mono text-sts-text">
                  {dmg.hits}
                </td>
                <td
                  className={`py-2 px-3 text-right font-mono ${
                    isTopHit ? "text-sts-amber font-bold" : "text-sts-text"
                  }`}
                >
                  {dmg.max_hit}
                </td>
                <td className="py-2 px-3 text-right font-mono">
                  {dmg.kills > 0 ? (
                    <span className="text-sts-red font-bold">{dmg.kills}</span>
                  ) : (
                    <span className="text-sts-text">0</span>
                  )}
                </td>
                <td className="py-2 px-3">
                  <div className="h-2 bg-sts-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-sts-red rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
