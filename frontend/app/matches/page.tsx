"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const COMPETITIONS = [
  { id: 39,  name: "Premier League",  logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png" },
  { id: 140, name: "La Liga",          logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png" },
  { id: 135, name: "Serie A",          logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png" },
  { id: 78,  name: "Bundesliga",       logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png" },
  { id: 61,  name: "Ligue 1",          logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png" },
  { id: 2,   name: "Champions League", logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/2.png" },
];

const SEASONS = [
  { value: 2025, label: "2025/26" },
  { value: 2024, label: "2024/25" },
  { value: 2023, label: "2023/24" },
  { value: 2022, label: "2022/23" },
  { value: 2021, label: "2021/22" },
];

const Spinner = () => (
  <div className="flex items-center gap-2 text-gray-400 text-sm">
    <div className="w-4 h-4 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
    Loading...
  </div>
);

export default function MatchesPage() {
  const router = useRouter();
  const [leagueId, setLeagueId] = useState<number | null>(null);
  const [season, setSeason] = useState(2024);
  const [teams, setTeams] = useState<any[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<any>(null);
  const [matches, setMatches] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const selectLeague = async (id: number) => {
    setLeagueId(id); setTeams([]); setSelectedTeam(null); setMatches([]); setHasMore(false); setOffset(0);
    setLoadingTeams(true);
    const res = await fetch(`${API}/league-teams/${id}?season=${season}`);
    const data = await res.json();
    setTeams(Array.isArray(data) ? data : []);
    setLoadingTeams(false);
  };

  const selectTeam = async (team: any) => {
    setSelectedTeam(team); setMatches([]); setHasMore(false); setOffset(0);
    setLoadingMatches(true);
    const res = await fetch(`${API}/team-matches/${team.id}?season=${season}&limit=5&offset=0`);
    const data = await res.json();
    setMatches(data.matches || []); setHasMore(data.hasMore || false); setOffset(5);
    setLoadingMatches(false);
  };

  const loadMore = async () => {
    if (!selectedTeam) return;
    setLoadingMore(true);
    const res = await fetch(`${API}/team-matches/${selectedTeam.id}?season=${season}&limit=5&offset=${offset}`);
    const data = await res.json();
    setMatches(prev => [...prev, ...(data.matches || [])]);
    setHasMore(data.hasMore || false); setOffset(prev => prev + 5);
    setLoadingMore(false);
  };

  const changeSeason = (s: number) => {
    setSeason(s); setTeams([]); setSelectedTeam(null); setMatches([]); setHasMore(false); setOffset(0);
    if (leagueId) {
      setLoadingTeams(true);
      fetch(`${API}/league-teams/${leagueId}?season=${s}`)
        .then(r => r.json())
        .then(data => { setTeams(Array.isArray(data) ? data : []); setLoadingTeams(false); })
        .catch(() => setLoadingTeams(false));
    }
  };

  return (
    <div className="relative min-h-screen text-white">
      <div className="parallax-bg" />
      <div className="relative max-w-4xl mx-auto px-4 pt-4 pb-20">

        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold drop-shadow-lg">Match Analysis</h1>
          <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-3 mb-2" />
          <p className="text-gray-400">Pick a league, season and team to browse matches</p>
        </div>

        {/* Step 1 — League */}
        <div className="mb-8">
          <p className="text-xs font-semibold text-white uppercase tracking-wider mb-3">1. Select competition</p>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-4">
            {COMPETITIONS.map((c) => (
              <button
                key={c.id}
                onClick={() => selectLeague(c.id)}
                className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition ${
                  leagueId === c.id
                    ? "border-green-500 bg-green-950/40"
                    : "border-white/10 bg-[#0f1923] hover:border-white/20"
                }`}
              >
                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center p-1">
                  <img src={c.logo} alt={c.name} className="w-8 h-8 object-contain" />
                </div>
                <span className="text-xs text-center leading-tight text-gray-300">{c.name}</span>
              </button>
            ))}
          </div>

          {/* Season */}
          <div className="flex items-center gap-3 mt-4">
            <span className="text-xs font-semibold text-white uppercase tracking-wider">Season</span>
            <select
              value={season}
              onChange={(e) => changeSeason(Number(e.target.value))}
              className="bg-[#0f1923] border border-white/20 rounded-lg px-4 py-2 text-sm text-white font-medium focus:outline-none focus:border-green-500 cursor-pointer"
            >
              {SEASONS.map((s) => (
                <option key={s.value} value={s.value} className="bg-[#0f1923]">{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Step 2 — Team */}
        {loadingTeams && <div className="mb-6"><Spinner /></div>}
        {teams.length > 0 && (
          <div className="mb-8">
            <p className="text-xs font-semibold text-white uppercase tracking-wider mb-3">2. Select a team</p>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
              {teams.map((t) => (
                <button
                  key={t.id}
                  onClick={() => selectTeam(t)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition ${
                    selectedTeam?.id === t.id
                      ? "border-green-500 bg-green-950/40"
                      : "border-white/10 bg-[#0f1923] hover:border-white/20"
                  }`}
                >
                  <div className="bg-white rounded-lg p-1 w-10 h-10 flex items-center justify-center">
                    <img src={t.logo} alt={t.name} className="w-7 h-7 object-contain" />
                  </div>
                  <span className="text-xs text-center leading-tight text-gray-300">{t.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3 — Matches */}
        {loadingMatches && <div className="mb-6"><Spinner /></div>}
        {matches.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-white uppercase tracking-wider mb-3">3. Select a match to analyse</p>
            <div className="space-y-2">
              {matches.map((m) => (
                <div
                  key={m.fixture_id}
                  onClick={() => router.push(`/match/${m.fixture_id}`)}
                  className="bg-[#0f1923] hover:bg-white/5 border border-white/10 hover:border-green-500/30 rounded-xl p-4 cursor-pointer transition"
                >
                  <p className="text-xs text-gray-600 mb-3">
                    {new Date(m.date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                  </p>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2 flex-1">
                      <img src={m.home_logo} className="w-7 h-7 object-contain flex-shrink-0" alt={m.home} />
                      <span className="font-medium text-sm truncate">{m.home}</span>
                    </div>
                    <div className="text-center flex-shrink-0">
                      <span className="text-xl font-bold tabular-nums">{m.score.home} – {m.score.away}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-1 justify-end">
                      <span className="font-medium text-sm truncate text-right">{m.away}</span>
                      <img src={m.away_logo} className="w-7 h-7 object-contain flex-shrink-0" alt={m.away} />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {hasMore && (
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="mt-4 w-full py-3 bg-[#0f1923] hover:bg-white/5 border border-white/10 rounded-xl text-sm text-gray-400 transition disabled:opacity-50"
              >
                {loadingMore ? "Loading..." : "Show 5 more matches"}
              </button>
            )}
          </div>
        )}

        {!loadingMatches && selectedTeam && matches.length === 0 && (
          <p className="text-gray-500 text-sm">No finished matches found for {selectedTeam.name} in this season.</p>
        )}
      </div>
    </div>
  );
}
