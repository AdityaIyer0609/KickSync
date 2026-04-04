"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PulseDot = () => (
  <span className="relative flex h-2 w-2">
    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
  </span>
);

const StatBar = ({ label, home, away }: { label: string; home: string; away: string }) => {
  const h = parseFloat(home) || 0;
  const a = parseFloat(away) || 0;
  const total = h + a || 1;
  const hPct = (h / total) * 100;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-semibold text-white w-10">{home}</span>
        <span className="text-gray-500">{label}</span>
        <span className="font-semibold text-white w-10 text-right">{away}</span>
      </div>
      <div className="flex h-1 rounded-full overflow-hidden bg-white/5">
        <div className="bg-green-500 transition-all" style={{ width: `${hPct}%` }} />
        <div className="bg-blue-500 flex-1" />
      </div>
    </div>
  );
};

const STAT_KEYS = ["possessionPct", "totalShots", "shotsOnTarget", "wonCorners", "foulsCommitted", "shotAssists"];
const STAT_LABELS: Record<string, string> = {
  possessionPct: "Possession %",
  totalShots: "Shots",
  shotsOnTarget: "Shots on Target",
  wonCorners: "Corners",
  foulsCommitted: "Fouls",
  shotAssists: "Shot Assists",
};

export default function LivePage() {
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "in" | "pre" | "post">("all");

  const load = async () => {
    try {
      const r = await fetch(`${API}/dashboard/live-scores`);
      const data = await r.json();
      setMatches(data);
    } catch {
      setMatches([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === "all" ? matches : matches.filter(m => m.state === filter);
  const liveCount = matches.filter(m => m.state === "in").length;

  return (
    <div className="relative min-h-screen text-white">
      <div className="parallax-bg" />
      <div className="relative max-w-4xl mx-auto px-4 pt-20 sm:pt-24 pb-20">

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl sm:text-4xl font-bold drop-shadow-lg">Live Scores</h1>
            {liveCount > 0 && (
              <span className="flex items-center gap-1.5 bg-green-500/30 border border-green-400 text-green-300 text-xs font-semibold px-2.5 py-1 rounded-full">
                <PulseDot /> {liveCount} Live
              </span>
            )}
          </div>
          <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-2 mb-3" />
          <p className="text-gray-400 text-sm">Scores refresh every 30 seconds</p>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-6">
          {(["all", "in", "pre", "post"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition border ${
                filter === f
                  ? "bg-green-500/40 border-green-400 text-green-300"
                  : "border-white/30 text-white bg-white/10 hover:border-green-500/40 hover:text-green-400"
              }`}>
              {f === "all" ? "All" : f === "in" ? "Live" : f === "pre" ? "Upcoming" : "Finished"}
            </button>
          ))}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20 text-gray-400">
            <div className="w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full animate-spin mr-3" />
            Loading matches...
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="text-center py-20 text-gray-500">
            <p className="text-lg mb-1">No matches found</p>
            <p className="text-sm">Try a different filter or check back later</p>
          </div>
        )}

        <div className="space-y-3">
          {filtered.map(m => {
            const isLive = m.state === "in";
            const isExpanded = expanded === m.id;
            const hasStats = Object.keys(m.stats).length > 0;

            return (
              <div key={m.id}
                className={`bg-[#0f1923] border rounded-2xl overflow-hidden transition-all duration-300 ${
                  isLive ? "border-green-500/30" : "border-white/10"
                }`}>

                {/* Match row */}
                <div
                  className={`p-4 sm:p-5 ${hasStats ? "cursor-pointer hover:bg-white/5" : ""}`}
                  onClick={() => hasStats && setExpanded(isExpanded ? null : m.id)}
                >
                  {/* League + status */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-500">{m.league}</span>
                    <div className="flex items-center gap-2">
                      {isLive ? (
                        <span className="flex items-center gap-1.5 text-xs text-green-400 font-semibold">
                          <PulseDot /> {m.clock || "Live"}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-500">{m.detail}</span>
                      )}
                    </div>
                  </div>

                  {/* Teams + score */}
                  <div className="flex items-start gap-2">
                    {/* Home */}
                    <div className="flex flex-col flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        {m.home.logo && <img src={m.home.logo} className="w-6 h-6 object-contain flex-shrink-0" alt={m.home.name} />}
                        <span className={`text-xs sm:text-sm font-semibold leading-tight ${m.home.winner ? "text-white" : "text-gray-300"}`}>
                          {m.home.name}
                        </span>
                      </div>
                      {m.home.goals?.length > 0 && (
                        <div className="mt-1 pl-7 space-y-0.5">
                          {m.home.goals.map((g: string, i: number) => (
                            <p key={i} className="text-[11px] text-gray-400 flex items-center gap-1">
                              <span>⚽</span> {g}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Score */}
                    <div className="flex-shrink-0 text-center w-16 pt-0.5">
                      {m.state === "pre" ? (
                        <span className="text-gray-500 text-sm">vs</span>
                      ) : (
                        <span className={`text-lg font-black tabular-nums ${isLive ? "text-green-400" : "text-white"}`}>
                          {m.home.score}–{m.away.score}
                        </span>
                      )}
                    </div>

                    {/* Away */}
                    <div className="flex flex-col flex-1 min-w-0 items-end">
                      <div className="flex items-center gap-1.5 justify-end">
                        <span className={`text-xs sm:text-sm font-semibold leading-tight text-right ${m.away.winner ? "text-white" : "text-gray-300"}`}>
                          {m.away.name}
                        </span>
                        {m.away.logo && <img src={m.away.logo} className="w-6 h-6 object-contain flex-shrink-0" alt={m.away.name} />}
                      </div>
                      {m.away.goals?.length > 0 && (
                        <div className="mt-1 pr-7 space-y-0.5 text-right">
                          {m.away.goals.map((g: string, i: number) => (
                            <p key={i} className="text-[11px] text-gray-400 flex items-center justify-end gap-1">
                              {g} <span>⚽</span>
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Venue + expand hint */}
                  {(m.venue || hasStats) && (
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs text-gray-600">{m.venue}</span>
                      {hasStats && (
                        <button className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border transition ${
                          isExpanded
                            ? "bg-green-500/20 border-green-500/40 text-green-400"
                            : "bg-white/5 border-white/15 text-gray-300 hover:border-green-500/40 hover:text-green-400"
                        }`}>
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d={isExpanded ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"} />
                          </svg>
                          {isExpanded ? "Hide Stats" : "Show Stats"}
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Stats panel */}
                {isExpanded && hasStats && (
                  <div className="border-t border-white/10 bg-white/[0.03] px-4 sm:px-5 py-5">
                    <div className="flex justify-between text-xs font-semibold mb-5">
                      <span className="flex items-center gap-1.5 text-green-400">
                        <span className="w-2.5 h-2.5 bg-green-500 rounded-full inline-block" />
                        {m.home.shortName || m.home.name}
                      </span>
                      <span className="text-gray-500 uppercase tracking-widest text-[10px]">Match Stats</span>
                      <span className="flex items-center gap-1.5 text-blue-400">
                        {m.away.shortName || m.away.name}
                        <span className="w-2.5 h-2.5 bg-blue-500 rounded-full inline-block" />
                      </span>
                    </div>
                    {STAT_KEYS.map(key => {
                      const hVal = m.stats[m.home.name]?.[key];
                      const aVal = m.stats[m.away.name]?.[key];
                      if (!hVal && !aVal) return null;
                      return (
                        <StatBar key={key} label={STAT_LABELS[key] || key}
                          home={hVal ?? "0"} away={aVal ?? "0"} />
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
