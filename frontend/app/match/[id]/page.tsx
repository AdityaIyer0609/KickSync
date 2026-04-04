"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const IconBack = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
  </svg>
);

const IconBall = () => (
  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
    <circle cx="12" cy="12" r="10" fill="white" stroke="#ccc" strokeWidth="1"/>
    <path d="M12 2a10 10 0 100 20A10 10 0 0012 2zm0 2c1.3 0 2.5.3 3.6.8L12 8.5 8.4 4.8A8 8 0 0112 4zm-5 1.6L10.5 9H5.1A8 8 0 017 5.6zm10 0A8 8 0 0118.9 9h-5.4l3.5-3.4zM4.5 11h6l-2 6.2A8 8 0 014.5 11zm9 0h6a8 8 0 01-4 6.2L13.5 11zm-4.8 7.4l2.3-5.8 2.3 5.8a8 8 0 01-4.6 0z" fill="#333"/>
  </svg>
);

const IconCard = ({ color }: { color: string }) => (
  <div className={`w-3 h-4 rounded-sm flex-shrink-0 ${color === "yellow" ? "bg-yellow-400" : "bg-red-500"}`} />
);

const IconAI = () => (
  <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
  </svg>
);

export default function MatchPage() {
  const { id } = useParams();
  const router = useRouter();
  const searchParams = useSearchParams ? useSearchParams() : null;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const slug = searchParams?.get("slug") || "";
    const url = slug ? `${API}/match/${id}?slug=${slug}` : `${API}/match/${id}`;
    fetch(url)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); window.scrollTo({ top: 0 }); })
      .catch(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="relative min-h-screen text-white">
      <div className="parallax-bg" />
      <div className="relative max-w-4xl mx-auto px-4 pt-24 pb-20">
        <div className="text-center text-gray-400">
          <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm">Loading match analysis...</p>
        </div>
      </div>
    </div>
  );

  if (!data || data.error) return (
    <div className="relative min-h-screen text-white">
      <div className="parallax-bg" />
      <div className="relative max-w-4xl mx-auto px-4 pt-24 pb-20">
        <p className="text-gray-400">Match not found</p>
      </div>
    </div>
  );

  const homeTeam = data.homeTeam;
  const awayTeam = data.awayTeam;

  return (
    <div className="relative min-h-screen text-white">
      <div className="parallax-bg" />
      <div className="relative max-w-4xl mx-auto px-4 pt-20 pb-20">

        {/* Back */}
        <button onClick={() => router.back()} className="flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-6 transition">
          <IconBack /> Back
        </button>

        {/* Match Header */}
        <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-4 sm:p-6 mb-6">
          <p className="text-xs text-gray-500 text-center mb-4 uppercase tracking-wider">
            {new Date(data.date).toLocaleDateString("en-GB", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </p>
          <div className="flex items-center justify-center gap-3 sm:gap-6">
            <div className="text-center flex-1">
              {data.homeLogo && <img src={data.homeLogo} alt={homeTeam} className="w-12 h-12 sm:w-16 sm:h-16 object-contain mx-auto mb-2 sm:mb-3 bg-white rounded-xl p-1.5" />}
              <p className="text-sm sm:text-lg font-bold leading-tight">{homeTeam}</p>
              <p className="text-gray-500 text-xs mt-1 hidden sm:block">{data.lineups?.[homeTeam]?.formation}</p>
            </div>
            <div className="text-center px-2 sm:px-4 flex-shrink-0">
              <p className="text-3xl sm:text-5xl font-black tabular-nums">{data.score.home} – {data.score.away}</p>
              <p className="text-xs text-gray-500 mt-1 sm:mt-2 uppercase tracking-wider">Full Time</p>
            </div>
            <div className="text-center flex-1">
              {data.awayLogo && <img src={data.awayLogo} alt={awayTeam} className="w-12 h-12 sm:w-16 sm:h-16 object-contain mx-auto mb-2 sm:mb-3 bg-white rounded-xl p-1.5" />}
              <p className="text-sm sm:text-lg font-bold leading-tight">{awayTeam}</p>
              <p className="text-gray-500 text-xs mt-1 hidden sm:block">{data.lineups?.[awayTeam]?.formation}</p>
            </div>
          </div>
          {/* Formation/coach below on mobile */}
          <div className="flex justify-between mt-3 sm:hidden text-xs text-gray-500">
            <span>{data.lineups?.[homeTeam]?.formation} · {data.lineups?.[homeTeam]?.coach}</span>
            <span className="text-right">{data.lineups?.[awayTeam]?.formation} · {data.lineups?.[awayTeam]?.coach}</span>
          </div>
        </div>

        {/* Stats */}
        {data.stats && Object.keys(data.stats).length > 0 && (() => {
          const statRows = [
            "Possession Percentage", "Shots", "Shots On Target", "Corners Won",
            "Fouls Committed", "Tackles Won", "Interceptions",
            "Passes", "Pass Percentage", "Yellow Cards",
            "Shots Blocked", "Clearances", "Saves",
          ];
          return (
            <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-5 mb-6">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Match Statistics</p>
              <div className="space-y-4">
                {statRows.map((stat) => {
                  const hv = data.stats[homeTeam]?.[stat] ?? "—";
                  const av = data.stats[awayTeam]?.[stat] ?? "—";
                  const isPercent = stat === "Possession Percentage" || stat === "Pass Percentage";
                  const hvDisplay = hv !== "—" && isPercent ? `${hv}%` : hv;
                  const avDisplay = av !== "—" && isPercent ? `${av}%` : av;
                  const label = stat === "Possession Percentage" ? "Possession %" 
                    : stat === "Pass Percentage" ? "Pass %" 
                    : stat === "Fouls Committed" ? "Fouls"
                    : stat === "Corners Won" ? "Corners"
                    : stat === "Shots On Target" ? "Shots on Target"
                    : stat === "Shots Blocked" ? "Blocked Shots"
                    : stat;
                  const hNum = parseFloat(String(hv)) || 0;
                  const aNum = parseFloat(String(av)) || 0;
                  const total = hNum + aNum || 1;
                  const hPct = (hNum / total) * 100;
                  return (
                    <div key={stat}>
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className="font-semibold text-white w-12">{hvDisplay}</span>
                        <span className="text-gray-500 text-xs">{label}</span>
                        <span className="font-semibold text-white w-12 text-right">{avDisplay}</span>
                      </div>
                      <div className="flex h-1 rounded-full overflow-hidden bg-white/5">
                        <div className="bg-green-500 transition-all" style={{ width: `${hPct}%` }} />
                        <div className="bg-blue-500 flex-1" />
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-4 text-xs text-gray-500">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-green-500 rounded-full inline-block" />{homeTeam}</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-blue-500 rounded-full inline-block" />{awayTeam}</span>
              </div>
            </div>
          );
        })()}

        {/* Data note */}
        {data.dataNote && (
          <div className="bg-yellow-950/40 border border-yellow-700/30 rounded-xl p-3 mb-6 text-yellow-300 text-sm">
            {data.dataNote}
          </div>
        )}

        {/* AI Analysis */}
        {data.analysis && (
          <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <IconAI />
              <p className="text-sm font-semibold text-white">AI Tactical Analysis</p>
            </div>
            <div className="text-gray-200 text-sm leading-7">
              <ReactMarkdown components={{
                h1: ({children}) => <h1 className="text-base font-bold text-green-400 mt-5 mb-2 border-b border-white/10 pb-1">{children}</h1>,
                h2: ({children}) => <h2 className="text-sm font-bold text-green-400 mt-5 mb-2 border-b border-white/10 pb-1">{children}</h2>,
                h3: ({children}) => <h3 className="text-sm font-semibold text-green-300 mt-4 mb-1">{children}</h3>,
                strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
                p: ({children}) => <p className="mb-3 text-gray-300">{children}</p>,
                ul: ({children}) => <ul className="space-y-2 mb-3 pl-1">{children}</ul>,
                li: ({children}) => (
                  <li className="flex gap-2 text-gray-300">
                    <span className="text-green-500 mt-1 shrink-0">–</span>
                    <span>{children}</span>
                  </li>
                ),
              }}>
                {data.analysis.replace(/<br\s*\/?>/gi, "\n")}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Goals & Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-5">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Goals</p>
            {data.goals.length === 0
              ? <p className="text-gray-600 text-sm">No goals recorded</p>
              : (
                <div className="space-y-2">
                  {data.goals.map((g: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span className="text-gray-600 font-mono text-xs w-10 flex-shrink-0">{g.minute}</span>
                      <IconBall />
                      <span className="font-medium flex-1">{g.player || "—"}</span>
                      {g.team && <span className={`text-xs px-2 py-0.5 rounded-full border ${g.team === homeTeam ? "border-green-700/40 text-green-400" : "border-blue-700/40 text-blue-400"}`}>{g.team === homeTeam ? "H" : "A"}</span>}
                      {g.detail?.includes("Own Goal") && <span className="text-red-400 text-xs">OG</span>}
                    </div>
                  ))}
                </div>
              )}
          </div>

          <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-5">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Cards</p>
            {data.cards.length === 0
              ? <p className="text-gray-600 text-sm">No cards recorded</p>
              : (
                <div className="space-y-2">
                  {data.cards.map((c: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span className="text-gray-600 font-mono text-xs w-10 flex-shrink-0">{c.minute}</span>
                      <IconCard color={c.card === "Yellow Card" ? "yellow" : "red"} />
                      <span className="font-medium flex-1">{c.player}</span>
                      {c.team && <span className={`text-xs px-2 py-0.5 rounded-full border ${c.team === homeTeam ? "border-green-700/40 text-green-400" : "border-blue-700/40 text-blue-400"}`}>{c.team === homeTeam ? "H" : "A"}</span>}
                    </div>
                  ))}
                </div>
              )}
          </div>
        </div>

        {/* Lineups */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[homeTeam, awayTeam].map((team, ti) => (
            <div key={team} className="bg-[#0f1923] border border-white/10 rounded-2xl p-5">
              <p className="font-semibold text-white mb-1">{team}</p>
              <p className="text-gray-500 text-xs mb-3">
                {data.lineups?.[team]?.formation} · {data.lineups?.[team]?.coach}
              </p>
              <div className="space-y-1.5">
                {data.lineups?.[team]?.startXI?.map((p: string, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className={`text-xs font-mono w-5 flex-shrink-0 ${ti === 0 ? "text-green-600" : "text-blue-600"}`}>{i + 1}</span>
                    <span className="text-gray-300">{p}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
