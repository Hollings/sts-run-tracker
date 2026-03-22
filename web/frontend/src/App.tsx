import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import LiveRun from "./pages/LiveRun";
import RunHistory from "./pages/RunHistory";
import RunDetail from "./pages/RunDetail";
import Stats from "./pages/Stats";
import { useWebSocket } from "./hooks/useWebSocket";

export default function App() {
  const { data, connected } = useWebSocket();

  return (
    <div className="min-h-screen bg-sts-bg text-sts-text">
      <Navbar connected={connected} />
      <main>
        <Routes>
          <Route path="/" element={<LiveRun data={data} />} />
          <Route path="/history" element={<RunHistory />} />
          <Route path="/history/:filename" element={<RunDetail />} />
          <Route path="/stats" element={<Stats />} />
        </Routes>
      </main>
    </div>
  );
}
