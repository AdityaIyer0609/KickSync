"use client";
import { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// SVG icon components
const IconArrow = () => (
  <svg className="w-3 h-3 text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
  </svg>
);

const IconTransfer = () => (
  <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
  </svg>
);

const IconTrophy = () => (
  <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0" />
  </svg>
);

const IconClub = () => (
  <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
  </svg>
);

const IconAI = () => (
  <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
  </svg>
);

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const sendQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResponse(null);
    try {
      const res = await fetch(`${API}/agent?query=${encodeURIComponent(query)}`, { method: "POST" });
      const data = await res.json();
      setResponse(data);
    } catch {
      setResponse({ source: "error", data: "Could not connect to backend" });
    }
    setLoading(false);
  };

  const renderData = (raw: any): React.ReactNode => {
    if (raw === null || raw === undefined) return null;
    if (typeof raw === "string" && raw.trim() === "") return <p className="text-gray-400 text-sm">No response.</p>;

    if (typeof raw === "string") {
      const cleaned = raw.replace(/<br\s*\/?>/gi, "\n");
      return (
        <div className="text-gray-200 leading-relaxed">
          <ReactMarkdown components={{
            h1: ({children}) => <h1 className="text-xl font-bold text-green-400 mt-4 mb-2">{children}</h1>,
            h2: ({children}) => <h2 className="text-lg font-bold text-green-400 mt-3 mb-2">{children}</h2>,
            h3: ({children}) => <h3 className="text-base font-semibold text-green-300 mt-2 mb-1">{children}</h3>,
            strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
            p: ({children}) => <p className="mb-3 text-gray-200">{children}</p>,
            ul: ({children}) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
            ol: ({children}) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
            li: ({children}) => <li className="text-gray-200 mb-1">{children}</li>,
            code: ({children}) => <code className="bg-white/5 px-1 rounded text-green-300 text-sm">{children}</code>,
          }}>{cleaned}</ReactMarkdown>
        </div>
      );
    }

    if (Array.isArray(raw)) {
      if (raw.length === 0) return <p className="text-gray-500 text-sm">No results found.</p>;

      // Club count ranking
      if (raw[0]?.club !== undefined && raw[0]?.count !== undefined) {
        return (
          <div className="space-y-3">
            <p className="text-xs text-gray-500 italic mb-4 border-l-2 border-white/10 pl-3">
              Results include first teams, reserve teams, and youth sides. Squad data may not reflect the very latest transfers.
            </p>
            {raw.map((item: any, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-gray-600 w-5 text-xs font-mono">{i + 1}</span>
                <div className="flex-1">
                  <div className="flex justify-between mb-1.5">
                    <span className="text-sm font-medium text-white">{item.club}</span>
                    <span className="text-green-400 font-bold text-sm tabular-nums">{item.count}</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full">
                    <div className="h-1 bg-gradient-to-r from-green-600 to-green-400 rounded-full" style={{ width: `${(item.count / raw[0].count) * 100}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      }

      // Player list with club
      if (raw[0]?.player !== undefined && raw[0]?.club !== undefined) {
        const grouped: Record<string, any[]> = {};
        raw.forEach((p: any) => { grouped[p.club || "Unknown"] = [...(grouped[p.club || "Unknown"] || []), p]; });
        return (
          <div className="space-y-5">
            <p className="text-xs text-gray-500 italic border-l-2 border-white/10 pl-3">
              Results include first teams, reserve teams, and youth sides. Player data may not reflect the most recent transfers.
            </p>
            {Object.entries(grouped).map(([club, players]) => (
              <div key={club}>
                <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">{club}</p>
                <div className="flex flex-wrap gap-2">
                  {players.map((p: any) => (
                    <span key={p.player} className="bg-white/5 border border-white/10 px-3 py-1 rounded-lg text-xs text-gray-200">
                      {p.player}{p.position ? <span className="text-gray-500"> · {p.position}</span> : ""}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        );
      }

      // Squad list (name + position)
      if (raw[0]?.name !== undefined && raw[0]?.position !== undefined) {
        const grouped: Record<string, string[]> = {};
        raw.forEach((p: any) => { grouped[p.position] = [...(grouped[p.position] || []), p.name]; });
        return (
          <div className="space-y-4">
            {Object.entries(grouped).map(([pos, players]) => (
              <div key={pos}>
                <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">{pos}</p>
                <div className="flex flex-wrap gap-2">
                  {players.map((p) => <span key={p} className="bg-white/5 border border-white/10 px-3 py-1 rounded-lg text-sm text-gray-200">{p}</span>)}
                </div>
              </div>
            ))}
          </div>
        );
      }

      // Simple string list (player names)
      if (typeof raw[0] === "string") {
        return (
          <div>
            <p className="text-xs text-gray-500 italic mb-4 border-l-2 border-white/10 pl-3">
              Results are based on transfer records in our database and may not include every player.
            </p>
            <div className="flex flex-wrap gap-2">
              {raw.map((item: string, i: number) => (
                <span key={i} className="bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg text-sm text-gray-200">{item}</span>
              ))}
            </div>
          </div>
        );
      }

      return <pre className="text-sm text-gray-300 overflow-auto">{JSON.stringify(raw, null, 2)}</pre>;
    }

    if (typeof raw === "object") {
      // Transfer history
      if (raw.transfers && Array.isArray(raw.transfers)) {
        return (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <IconTransfer />
              <p className="text-sm font-semibold text-white">Transfer History — <span className="text-green-400 capitalize">{raw.player}</span></p>
            </div>
            <p className="text-xs text-gray-500 italic mb-4 border-l-2 border-white/10 pl-3">
              Transfer records are sourced from our database and may not include every move or reflect the most recent activity.
            </p>
            <div className="space-y-2">
              {raw.transfers.map((t: any, i: number) => (
                <div key={i} className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3">
                  <span className="text-gray-600 text-xs font-mono w-12 flex-shrink-0">{t.season || "—"}</span>
                  <span className="text-gray-300 text-sm flex-1 truncate">{t.from_club || "—"}</span>
                  <IconArrow />
                  <span className="text-white text-sm font-medium flex-1 truncate text-right">{t.to_club || "—"}</span>
                  {t.fee && <span className="text-green-400 text-xs ml-2 flex-shrink-0">{t.fee}</span>}
                </div>
              ))}
            </div>
          </div>
        );
      }

      // Clubs list
      if (raw.clubs && Array.isArray(raw.clubs)) {
        return (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <IconClub />
              <p className="text-sm font-semibold text-white">Career Clubs — <span className="text-green-400 capitalize">{raw.player}</span></p>
            </div>
            <div className="flex flex-wrap gap-2">
              {raw.clubs.map((c: string, i: number) => (
                <span key={i} className="bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg text-sm text-gray-200">{c}</span>
              ))}
            </div>
          </div>
        );
      }

      // Player profile (API)
      if (raw.name && raw.nationality) {
        return (
          <div>
            <div className="mb-4">
              <h3 className="text-2xl font-bold text-white">{raw.name}</h3>
              <p className="text-gray-400 text-sm mt-1">{raw.nationality} · {raw.position} · Age {raw.age}</p>
              <p className="text-gray-400 text-sm">Current Team: <span className="text-white font-medium">{raw.currentTeam}</span></p>
            </div>
            {raw.season2024 && (
              <div className="bg-white/5 border border-white/10 rounded-xl p-4 mb-4">
                <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-3">{raw.seasonLabel || "2024/25"} Season</p>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: "Goals", val: raw.season2024.goals },
                    { label: "Assists", val: raw.season2024.assists },
                    { label: "Apps", val: raw.season2024.appearances },
                    { label: "Yellows", val: raw.season2024.yellowCards },
                    { label: "Reds", val: raw.season2024.redCards },
                    { label: "Rating", val: raw.season2024.rating ? Number(raw.season2024.rating).toFixed(2) : null },
                  ].map(({ label, val }) => (
                    <div key={label} className="text-center bg-white/5 border border-white/5 rounded-lg py-3">
                      <p className="text-2xl font-bold text-white">{val ?? "—"}</p>
                      <p className="text-gray-500 text-xs mt-1">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {raw.trophiesWon?.length > 0 && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <IconTrophy />
                  <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider">Trophies</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {raw.trophiesWon.map((t: string, i: number) => (
                    <span key={i} className="bg-yellow-900/20 border border-yellow-700/30 text-yellow-300 px-2 py-1 rounded-lg text-xs">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {raw.transferHistory?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <IconTransfer />
                  <p className="text-xs font-semibold text-green-400 uppercase tracking-wider">Transfer History</p>
                </div>
                <div className="space-y-1.5">
                  {raw.transferHistory.map((t: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm">
                      <span className="text-gray-600 font-mono text-xs w-10 flex-shrink-0">{t.date?.slice(0, 4)}</span>
                      <span className="text-gray-300 flex-1 truncate">{t.from}</span>
                      <IconArrow />
                      <span className="text-white font-medium flex-1 truncate text-right">{t.to}</span>
                      {t.fee && <span className="text-gray-500 text-xs ml-2">({t.fee})</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      }

      return <pre className="text-sm text-gray-300 overflow-auto">{JSON.stringify(raw, null, 2)}</pre>;
    }

    return <pre className="text-sm text-gray-300 overflow-auto">{JSON.stringify(raw, null, 2)}</pre>;
  };

  const suggestions = [
    "show arsenal squad", "mbappe stats", "which club has the most brazilians",
    "which premier league club has the most attackers",
    "players who played for both manchester city and barcelona",
    "show all brazilian players in premier league",
    "show all attackers in barcelona"
  ];

  return (
    <div className="relative min-h-screen text-white">
      <div className="parallax-bg" />
      <div className="relative max-w-3xl mx-auto px-4 pt-4 pb-20">

        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold drop-shadow-lg">Football Assistant</h1>
          <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-3 mb-2" />
          <p className="text-gray-400">Ask about squads, player stats, tactics, transfers and more</p>
        </div>

        {/* Input */}
        <div className="flex gap-3 mb-6">
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendQuery()}
            placeholder="e.g. mbappe stats, show arsenal squad, who plays for PSG"
            className="flex-1 bg-[#0f1923] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-green-500 transition"
            suppressHydrationWarning
          />
          <button
            onClick={sendQuery}
            disabled={loading}
            className="bg-green-600 hover:bg-green-500 disabled:opacity-50 px-6 py-3 rounded-xl font-semibold transition"
          >
            {loading ? "..." : "Ask"}
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="text-center py-10 text-gray-400">
            <div className="inline-block w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm">Thinking...</p>
          </div>
        )}

        {/* Response */}
        {response && (
          <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-5 shadow-xl shadow-black/40 mb-8">
            <div className="flex items-center gap-2 mb-4">
              {response.source === "llm_fallback" && (
                <span className="text-xs bg-yellow-900/30 text-yellow-300 border border-yellow-700/30 px-2.5 py-1 rounded-full">
                  API limit — stats estimated by AI
                </span>
              )}
            </div>
            {(response.source === "llm" || response.source === "llm_fallback") && (
              <div className="flex items-start gap-2 mb-4 border-l-2 border-white/10 pl-3">
                <IconAI />
                <p className="text-xs text-gray-500 italic">
                  AI-generated response based on training data. May not reflect the latest transfers or results.
                </p>
              </div>
            )}
            {renderData(response.data)}
          </div>
        )}

        {/* Suggestions */}
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wider mb-3">Try asking</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button key={s} onClick={() => {
                setQuery(s);
                inputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
                inputRef.current?.focus();
              }}
                className="text-xs bg-[#0f1923] hover:bg-white/10 border border-white/10 hover:border-green-500/40 text-gray-300 px-3 py-1.5 rounded-full transition">
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
