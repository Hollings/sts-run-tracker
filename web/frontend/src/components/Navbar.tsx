import React from "react";
import { Link, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Live Run" },
  { path: "/history", label: "Run History" },
  { path: "/stats", label: "Stats" },
];

interface Props {
  connected?: boolean;
}

export default function Navbar({ connected }: Props) {
  const location = useLocation();

  return (
    <nav className="bg-sts-surface border-b border-sts-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-lg font-bold text-sts-gold">
                StS2 Tracker
              </span>
            </Link>
            <div className="flex items-center gap-1">
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.path === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-sts-card text-sts-gold"
                        : "text-sts-text-dim hover:text-sts-text hover:bg-sts-card/50"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                connected ? "bg-sts-green" : "bg-sts-red"
              }`}
            />
            <span className="text-xs text-sts-text-dim">
              {connected ? "Live" : "Disconnected"}
            </span>
          </div>
        </div>
      </div>
    </nav>
  );
}
