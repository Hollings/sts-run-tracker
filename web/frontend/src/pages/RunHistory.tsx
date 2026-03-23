import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import type { RunSummary } from "../utils/types";
import { formatGameId, formatDuration, formatDate } from "../utils/format";

type SortField = "start_time" | "run_time" | "ascension" | "floor_count";
type SortDir = "asc" | "desc";

export default function RunHistory() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [charFilter, setCharFilter] = useState<string>("");
  const [resultFilter, setResultFilter] = useState<string>("");
  const [ascFilter, setAscFilter] = useState<string>("");

  // Sort
  const [sortField, setSortField] = useState<SortField>("start_time");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data) => {
        setRuns(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Extract unique characters for filter
  const allCharacters = useMemo(() => {
    const chars = new Set<string>();
    runs.forEach((r) => r.characters.forEach((c) => chars.add(c)));
    return Array.from(chars).sort();
  }, [runs]);

  // Extract unique ascensions for filter
  const allAscensions = useMemo(() => {
    const ascs = new Set<number>();
    runs.forEach((r) => ascs.add(r.ascension));
    return Array.from(ascs).sort((a, b) => a - b);
  }, [runs]);

  // Filter and sort
  const filteredRuns = useMemo(() => {
    let result = [...runs];

    if (charFilter) {
      result = result.filter((r) => r.characters.includes(charFilter));
    }
    if (resultFilter === "win") {
      result = result.filter((r) => r.win);
    } else if (resultFilter === "loss") {
      result = result.filter((r) => !r.win && !r.was_abandoned);
    } else if (resultFilter === "abandoned") {
      result = result.filter((r) => r.was_abandoned);
    }
    if (ascFilter) {
      result = result.filter((r) => r.ascension === parseInt(ascFilter));
    }

    result.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (sortDir === "asc") return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    });

    return result;
  }, [runs, charFilter, resultFilter, ascFilter, sortField, sortDir]);

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  }

  function sortIndicator(field: SortField) {
    if (sortField !== field) return "";
    return sortDir === "asc" ? " [asc]" : " [desc]";
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center text-sts-text py-12">Loading runs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center text-sts-red py-12">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-sts-gold mb-6">Run History</h1>

      {/* Filters */}
      <div className="bg-sts-surface border border-sts-border rounded-lg p-4 mb-6 flex flex-wrap gap-4">
        <div>
          <label className="block text-xs text-sts-text mb-1">
            Character
          </label>
          <select
            value={charFilter}
            onChange={(e) => setCharFilter(e.target.value)}
            className="bg-sts-card border border-sts-border rounded px-3 py-1.5 text-sm text-sts-text"
          >
            <option value="">All</option>
            {allCharacters.map((c) => (
              <option key={c} value={c}>
                {formatGameId(c)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-sts-text mb-1">
            Result
          </label>
          <select
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value)}
            className="bg-sts-card border border-sts-border rounded px-3 py-1.5 text-sm text-sts-text"
          >
            <option value="">All</option>
            <option value="win">Win</option>
            <option value="loss">Loss</option>
            <option value="abandoned">Abandoned</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-sts-text mb-1">
            Ascension
          </label>
          <select
            value={ascFilter}
            onChange={(e) => setAscFilter(e.target.value)}
            className="bg-sts-card border border-sts-border rounded px-3 py-1.5 text-sm text-sts-text"
          >
            <option value="">All</option>
            {allAscensions.map((a) => (
              <option key={a} value={a}>
                A{a}
              </option>
            ))}
          </select>
        </div>
        <div className="ml-auto self-end text-sm text-sts-text">
          {filteredRuns.length} of {runs.length} runs
        </div>
      </div>

      {/* Runs table */}
      <div className="bg-sts-surface border border-sts-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-sts-border bg-sts-card/50 text-sts-text text-left">
                <th
                  className="py-3 px-4 font-medium cursor-pointer hover:text-sts-text"
                  onClick={() => toggleSort("start_time")}
                >
                  Date{sortIndicator("start_time")}
                </th>
                <th className="py-3 px-4 font-medium">Character</th>
                <th
                  className="py-3 px-4 font-medium cursor-pointer hover:text-sts-text"
                  onClick={() => toggleSort("ascension")}
                >
                  Asc{sortIndicator("ascension")}
                </th>
                <th className="py-3 px-4 font-medium">Result</th>
                <th
                  className="py-3 px-4 font-medium cursor-pointer hover:text-sts-text"
                  onClick={() => toggleSort("run_time")}
                >
                  Time{sortIndicator("run_time")}
                </th>
                <th className="py-3 px-4 font-medium">Seed</th>
                <th
                  className="py-3 px-4 font-medium cursor-pointer hover:text-sts-text"
                  onClick={() => toggleSort("floor_count")}
                >
                  Floors{sortIndicator("floor_count")}
                </th>
                <th className="py-3 px-4 font-medium">Killed By</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => {
                const resultColor = run.win
                  ? "text-sts-green"
                  : run.was_abandoned
                  ? "text-sts-text"
                  : "text-sts-red";
                const resultText = run.win
                  ? "W"
                  : run.was_abandoned
                  ? "ABN"
                  : "L";
                return (
                  <tr
                    key={run.filename}
                    className="border-b border-sts-border/50 hover:bg-sts-card/30"
                  >
                    <td className="py-2.5 px-4">
                      <Link
                        to={`/history/${run.filename}`}
                        className="text-sts-gold hover:text-sts-gold-light underline"
                      >
                        {formatDate(run.start_time)}
                      </Link>
                    </td>
                    <td className="py-2.5 px-4 text-sts-gold-light">
                      {run.characters.map(formatGameId).join(", ")}
                    </td>
                    <td className="py-2.5 px-4 font-mono">
                      {run.ascension}
                    </td>
                    <td className={`py-2.5 px-4 font-bold ${resultColor}`}>
                      {resultText}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-sts-text">
                      {formatDuration(run.run_time)}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-sts-text">
                      {run.seed}
                    </td>
                    <td className="py-2.5 px-4 font-mono">
                      {run.floor_count}
                    </td>
                    <td className="py-2.5 px-4 text-sts-text">
                      {run.win ? "" : formatGameId(run.killed_by)}
                    </td>
                  </tr>
                );
              })}
              {filteredRuns.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="py-8 text-center text-sts-text"
                  >
                    No runs match your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
