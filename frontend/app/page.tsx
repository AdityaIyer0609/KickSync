"use client";
import { useEffect, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { StatCardSkeleton, MatchCardSkeleton } from "./components/Skeleton";

const IconChevronLeft = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);
const IconChevronRight = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
  </svg>
);

function Gallery({ children, speed, itemWidth, height }: { children: React.ReactNode[], speed: string, itemWidth: number, height: number }) {
  const outerRef = useRef<HTMLDivElement>(null);
  const posRef = useRef(0);          // current rendered X offset
  const targetRef = useRef(0);       // target X offset (accumulates clicks)
  const autoSpeedRef = useRef(speed === "slow" ? 0.4 : 1.2); // px per frame
  const manualRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rafRef = useRef<number>(0);
  const setWidthRef = useRef(0);     // total width of one set of items

  // Measure set width after mount
  useEffect(() => {
    const outer = outerRef.current;
    if (!outer) return;
    const set = outer.querySelector<HTMLDivElement>(".gallery-set");
    if (set) setWidthRef.current = set.scrollWidth;
  }, [children]);

  useEffect(() => {
    const outer = outerRef.current;
    if (!outer) return;

    const sets = outer.querySelectorAll<HTMLDivElement>(".gallery-set");

    const tick = () => {
      const W = setWidthRef.current;

      if (!manualRef.current) {
        // Auto-scroll: move left continuously
        posRef.current -= autoSpeedRef.current;
        targetRef.current = posRef.current;
      } else {
        // Manual: ease toward target
        posRef.current += (targetRef.current - posRef.current) * 0.15;
        if (Math.abs(targetRef.current - posRef.current) < 0.3) {
          posRef.current = targetRef.current;
        }
      }

      // Wrap posRef only — keep targetRef free so clicks don't jump
      if (W > 0) {
        const wrapped = ((posRef.current % W) - W) % W;
        const delta = wrapped - posRef.current;
        if (delta !== 0) {
          posRef.current = wrapped;
          targetRef.current += delta;
        }
      }

      sets.forEach((s, i) => {
        s.style.transform = `translateX(${posRef.current + i * W}px)`;
      });

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [children]);

  const scroll = (dir: number) => {
    if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    manualRef.current = true;
    targetRef.current += dir * itemWidth;

    resumeTimerRef.current = setTimeout(() => {
      manualRef.current = false;
    }, 3000);
  };

  return (
    <div className="relative group">
      <button onClick={() => scroll(1)}
        className="absolute left-2 top-1/2 -translate-y-1/2 z-10 bg-black/60 hover:bg-black/90 border border-white/10 rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <IconChevronLeft />
      </button>

      <div className="overflow-hidden" ref={outerRef} style={{ height }}>
        <div className="gallery-outer">
          <div className="gallery-set">{children}</div>
          <div className="gallery-set" aria-hidden>{children}</div>
        </div>
      </div>

      <button onClick={() => scroll(-1)}
        className="absolute right-2 top-1/2 -translate-y-1/2 z-10 bg-black/60 hover:bg-black/90 border border-white/10 rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <IconChevronRight />
      </button>
    </div>
  );
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Module-level cache — persists across navigation, cleared after 5 minutes
const CACHE_TTL = 5 * 60 * 1000;
const cache: Record<string, { data: any; ts: number }> = {};

async function cachedFetch(url: string) {
  const now = Date.now();
  if (cache[url] && now - cache[url].ts < CACHE_TTL) {
    return cache[url].data;
  }
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status}`);
  const data = await r.json();
  cache[url] = { data, ts: now };
  return data;
}

export default function Home() {
  const [inForm, setInForm] = useState<any[]>(() => cache[`${API}/dashboard/in-form`]?.data ?? []);
  const [bestDefense, setBestDefense] = useState<any[]>(() => cache[`${API}/dashboard/best-defense`]?.data ?? []);
  const [bestOffense, setBestOffense] = useState<any[]>(() => cache[`${API}/dashboard/best-offense`]?.data ?? []);
  const [spotlight, setSpotlight] = useState<any>(() => cache[`${API}/dashboard/spotlight`]?.data ?? null);
  const [matches, setMatches] = useState<any[]>(() => cache[`${API}/dashboard/recent-matches`]?.data ?? []);
  const [news, setNews] = useState<any[]>(() => cache[`${API}/dashboard/news`]?.data ?? []);

  useEffect(() => {
    const load = async (url: string, setter: (d: any) => void) => {
      try {
        const data = await cachedFetch(url);
        setter(data);
      } catch (e) {
        console.warn("Failed to fetch", url, e);
      }
    };
    load(`${API}/dashboard/in-form`, setInForm);
    load(`${API}/dashboard/best-defense`, setBestDefense);
    load(`${API}/dashboard/best-offense`, setBestOffense);
    load(`${API}/dashboard/spotlight`, setSpotlight);
    load(`${API}/dashboard/recent-matches`, setMatches);
    load(`${API}/dashboard/news`, setNews);
  }, []);

  const formColor = (r: string) =>
    r === "W" ? "bg-green-500" : r === "D" ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="relative min-h-screen text-white overflow-x-hidden">

      {/* 🌌 Background */}
      <div className="parallax-bg" />
      {/* CONTENT */}
      <div className="relative p-4 sm:p-6 pt-20 sm:pt-24 space-y-10">

        {/* HEADER */}
        <div>
          <div className="flex items-center gap-1 mb-1">
            <div className="w-12 h-12 sm:w-16 sm:h-16 overflow-hidden flex-shrink-0">
              <img src="/logo.png" alt="KickSync" className="w-full h-full object-cover scale-150 drop-shadow-[0_0_8px_rgba(0,0,0,0.9)]" />
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold drop-shadow-lg">KickSync</h1>
          </div>
          <p className="text-gray-300 mt-1 pl-4 sm:pl-5 text-sm sm:text-base">
            Where live football data meets AI-driven insights, analysis, and tactical intelligence
          </p>
        </div>

        {/* LATEST NEWS */}
        {news.length > 0 && (
          <section className="mt-10 sm:mt-80">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold tracking-tight text-white">Latest News</h2>
              <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-2" />
            </div>
            <Gallery speed="slow" itemWidth={304} height={280}>
              {news.map((article, i) => (
                <a
                  key={i}
                  href={article.link || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 w-72 rounded-xl overflow-hidden bg-[#0f1923] border border-white/10 hover:border-green-400/50 transition-all duration-300 shadow-xl shadow-black/40 cursor-pointer mr-4"
                >
                  {article.image && (
                    <img src={article.image} alt={article.headline} className="w-full h-40 object-cover" loading="lazy" width="288" height="160" />
                  )}
                  <div className="p-3">
                    <p className="text-sm font-semibold text-white leading-snug line-clamp-2">{article.headline}</p>
                    {article.description && (
                      <p className="text-xs text-gray-400 mt-1 line-clamp-2">{article.description}</p>
                    )}
                    {article.published && (
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(article.published).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                      </p>
                    )}
                  </div>
                </a>
              ))}
            </Gallery>
          </section>
        )}

        {/* RECENT MATCHES */}
        <section>
          <div className="mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-white">
              Recent Matches
            </h2>
            <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-2" />
          </div>
          {matches.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {matches.map((m, i) => (
                <div key={i} className="bg-[#0f1923] border border-white/10 rounded-2xl overflow-hidden shadow-xl shadow-black/40 hover:border-white/20 transition-all duration-300">
                  <div className="p-4">
                    {/* League + date */}
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs text-gray-500">{m.league}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(m.date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                      </span>
                    </div>
                    {/* Teams + score */}
                    <div className="flex items-start gap-2">
                      {/* Home */}
                      <div className="flex flex-col flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <img src={m.home_logo} className="w-6 h-6 object-contain flex-shrink-0" />
                          <span className="text-xs sm:text-sm font-semibold leading-tight text-gray-300">{m.home}</span>
                        </div>
                        {m.home_goals?.length > 0 && (
                          <div className="mt-1 pl-7 space-y-0.5">
                            {m.home_goals.map((g: string, j: number) => (
                              <p key={j} className="text-[11px] text-gray-400 flex items-center gap-1">
                                <span>⚽</span>{g}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                      {/* Score */}
                      <div className="flex-shrink-0 text-center w-16 pt-0.5">
                        <span className="text-lg font-black tabular-nums text-white">
                          {m.score.home}–{m.score.away}
                        </span>
                      </div>
                      {/* Away */}
                      <div className="flex flex-col flex-1 min-w-0 items-end">
                        <div className="flex items-center gap-1.5 justify-end">
                          <span className="text-xs sm:text-sm font-semibold leading-tight text-right text-gray-300">{m.away}</span>
                          <img src={m.away_logo} className="w-6 h-6 object-contain flex-shrink-0" />
                        </div>
                        {m.away_goals?.length > 0 && (
                          <div className="mt-1 pr-7 space-y-0.5 text-right">
                            {m.away_goals.map((g: string, j: number) => (
                              <p key={j} className="text-[11px] text-gray-400 flex items-center justify-end gap-1">
                                {g}<span>⚽</span>
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-400 text-sm">
              <MatchCardSkeleton />
            </div>
          )}
        </section>

        {/* AI INSIGHTS */}
        <section>
          <div className="mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-white">
              AI Insights
            </h2>
            <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-2" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            {/* In-form */}
            <div className="bg-[#0f1923] border border-white/10 p-4 rounded-xl shadow-xl shadow-black/40">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-white tracking-wide">
                  Most In-Form Teams
                </p>
                <div className="w-6 h-[2px] bg-green-400 rounded-full" />
              </div>
              <p className="text-xs text-gray-500 mb-3">Based on last 5 results across all competitions</p>
              {inForm.length > 0 ? inForm.map((t, i) => (
                <div key={i} className="flex justify-between mb-2">
                  <div>
                    <p className="text-sm">{t.team}</p>
                  </div>
                  <div className="flex gap-1">
                    {t.form.split("").map((r: string, j: number) => (
                      <span
                        key={j}
                        className={`w-5 h-5 rounded-full text-xs flex items-center justify-center ${formColor(r)}`}
                      >
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )) : <StatCardSkeleton />}
            </div>

            {/* Best defense */}
            <div className="bg-[#0f1923] border border-white/10 p-4 rounded-xl shadow-xl shadow-black/40">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-white tracking-wide">
                  Best Defence
                </p>
                <div className="w-6 h-[2px] bg-green-400 rounded-full" />
              </div>
              {bestDefense.length > 0 ? bestDefense.map((t, i) => (
                <div key={i} className="flex justify-between mb-2">
                  <div>
                    <p className="text-sm">{t.team}</p>
                    <p className="text-xs text-gray-500">{t.league}</p>
                  </div>
                  <span className="text-green-400 font-bold">{t.goalsAgainst} GA</span>
                </div>
              )) : <StatCardSkeleton />}
            </div>

            {/* Best Offense */}
            <div className="bg-[#0f1923] border border-white/10 p-4 rounded-xl shadow-xl shadow-black/40">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-white tracking-wide">
                  Best Attack
                </p>
                <div className="w-6 h-[2px] bg-green-400 rounded-full" />
              </div>
              {bestOffense.length > 0 ? bestOffense.map((t, i) => (
                <div key={i} className="flex justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium">{t.team}</p>
                    <p className="text-xs text-gray-500">{t.league}</p>
                  </div>
                  <span className="text-orange-400 font-bold">{t.goalsFor} GF</span>
                </div>
              )) : <StatCardSkeleton />}
            </div>

          </div>
        </section>

        {/* PLAYER SPOTLIGHT */}
        <section>
          <div className="mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-white">
              Player Spotlight
            </h2>
            <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-2" />
          </div>
          {spotlight && (
            <div className="bg-[#0f1923] border border-white/10 rounded-2xl p-4 sm:p-6 shadow-xl shadow-black/40 flex flex-col sm:flex-row gap-4 sm:gap-6 items-start">
              {spotlight.photo && (
                <img
                  src={spotlight.photo}
                  alt={spotlight.name}
                  className="w-full sm:w-28 max-h-48 sm:max-h-none rounded-xl flex-shrink-0 bg-gray-800 object-contain"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              )}
              <div className="flex-1">
                <h3 className="text-2xl font-bold mb-1">{spotlight.name}</h3>
                <p className="text-gray-300 text-sm mb-4">
                  {spotlight.club} · {spotlight.nationality}
                </p>
                <ReactMarkdown components={{
                  p: ({children}) => <p className="text-gray-300 text-sm mb-2 leading-relaxed">{children}</p>,
                  strong: ({children}) => (
                    <span className="block text-xs font-semibold text-green-400 uppercase tracking-wider mt-3 mb-1">
                      {children}
                    </span>
                  ),
                  ul: ({children}) => <ul className="space-y-1 mb-2">{children}</ul>,
                  li: ({children}) => <li className="text-gray-300 text-sm flex gap-2"><span className="text-green-500 mt-0.5">–</span><span>{children}</span></li>,
                }}>{spotlight.summary || ""}</ReactMarkdown>
              </div>
            </div>
          )}
        </section>

        {/* ICONIC MOMENTS */}
        <section>
          <div className="mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-white">Iconic Moments</h2>
            <div className="w-12 h-[2px] bg-gradient-to-r from-green-400 to-transparent mt-2" />
          </div>
          <Gallery speed="fast" itemWidth={400} height={320}>
            {["/pele.webp","/neymar.jpg","/ronaldo.jpg","/messi.jpg","/ronaldo1.webp","/zidane.jpg","/vini.webp"]
              .map((img, i) => (
                <img
                  key={i}
                  src={img}
                  className="h-75 md:h-80 w-96 object-cover object-center rounded-xl flex-shrink-0 mr-4"
                />
              ))}
          </Gallery>
        </section>

      </div>
    </div>
  );
}

