import React, { useState } from "react";
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
  const [copied, setCopied] = useState(false);

  const dashboardUrl = window.location.origin;

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(dashboardUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <nav className="bg-sts-gold sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-lg font-bold text-sts-bg">
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
                        ? "bg-sts-bg/20 text-sts-bg font-bold"
                        : "text-sts-bg/70 hover:text-sts-bg hover:bg-sts-bg/10"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleCopyUrl}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-sts-bg/10 hover:bg-sts-bg/20 transition-colors text-sts-bg/70 hover:text-sts-bg text-xs font-mono cursor-pointer"
              title="Click to copy dashboard URL"
            >
              <span>{dashboardUrl}</span>
              <span className="text-[10px]">{copied ? "(copied!)" : "(click to copy)"}</span>
            </button>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  connected ? "bg-sts-green" : "bg-sts-red"
                }`}
              />
              <span className="text-xs text-sts-bg/70">
                {connected ? "Live" : "Disconnected"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
