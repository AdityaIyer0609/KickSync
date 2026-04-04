import requests
import asyncio
import httpx
from fastapi import APIRouter
from config import API_KEY, API_FOOTBALL_KEY
from llm import chat

router = APIRouter()

FD_HEADERS = {"X-Auth-Token": API_KEY}
AF_HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

LEAGUE_MAP = {39: "PL", 140: "PD", 135: "SA", 78: "BL1", 61: "FL1", 2: "CL"}

# ESPN league slugs for each competition
ESPN_LEAGUE_MAP = {
    39: "eng.1",   # Premier League
    140: "esp.1",  # La Liga
    135: "ita.1",  # Serie A
    78: "ger.1",   # Bundesliga
    61: "fra.1",   # Ligue 1
    2: "uefa.champions",  # Champions League
}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

COMPETITIONS = [
    {"id": 39,  "name": "Premier League",  "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"id": 140, "name": "La Liga",          "flag": "🇪🇸"},
    {"id": 135, "name": "Serie A",          "flag": "🇮🇹"},
    {"id": 78,  "name": "Bundesliga",       "flag": "🇩🇪"},
    {"id": 61,  "name": "Ligue 1",          "flag": "🇫🇷"},
    {"id": 2,   "name": "Champions League", "flag": "🏆"},
]


@router.get("/competitions")
def get_competitions():
    return COMPETITIONS


@router.get("/league-teams/{league_id}")
def get_league_teams(league_id: int, season: int = 2023):
    espn_slug = ESPN_LEAGUE_MAP.get(league_id)
    if not espn_slug:
        return []
    r = requests.get(f"{ESPN_BASE}/{espn_slug}/teams")
    if r.status_code != 200:
        return []
    teams = r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    return [
        {
            "id": t["team"]["id"],
            "name": t["team"]["displayName"],
            "logo": t["team"].get("logos", [{}])[0].get("href", "") if t["team"].get("logos") else "",
            "espn_slug": espn_slug
        }
        for t in teams
    ]


ESPN_ALL_SLUGS = {
    **ESPN_LEAGUE_MAP,
    # Cups
    39001: "eng.fa", 39002: "eng.league_cup",
    140001: "esp.copa_del_rey",
    135001: "ita.coppa_italia",
    78001: "ger.dfb_pokal",
    61001: "fra.coupe_de_france",
    2001: "uefa.europa", 2002: "uefa.europa.conf",
}

SLUG_NAMES = {
    "eng.1": "Premier League", "esp.1": "La Liga", "ita.1": "Serie A",
    "ger.1": "Bundesliga", "fra.1": "Ligue 1", "uefa.champions": "Champions League",
    "eng.fa": "FA Cup", "eng.league_cup": "League Cup",
    "esp.copa_del_rey": "Copa del Rey", "ita.coppa_italia": "Coppa Italia",
    "ger.dfb_pokal": "DFB Pokal", "fra.coupe_de_france": "Coupe de France",
    "uefa.europa": "Europa League", "uefa.europa.conf": "Conference League",
}

CUP_SLUGS_BY_LEAGUE = {
    39: ["eng.fa", "eng.league_cup"],
    140: ["esp.copa_del_rey"],
    135: ["ita.coppa_italia"],
    78: ["ger.dfb_pokal"],
    61: ["fra.coupe_de_france"],
    2: ["uefa.europa", "uefa.europa.conf"],
}

@router.get("/team-matches/{team_id}")
def get_team_matches(team_id: int, season: int = 2024, limit: int = 5, offset: int = 0):
    # Find which league this team belongs to
    league_slug = None
    league_events = []
    for league_id, slug in ESPN_LEAGUE_MAP.items():
        r = requests.get(f"{ESPN_BASE}/{slug}/teams/{team_id}/schedule?season={season}")
        if r.status_code == 200 and r.json().get("events"):
            league_slug = slug
            league_events = [(e, slug) for e in r.json()["events"]]
            break

    if not league_slug:
        return {"matches": [], "hasMore": False}

    # Also fetch cup matches for this league's country
    league_id_found = next((lid for lid, s in ESPN_LEAGUE_MAP.items() if s == league_slug), None)
    cup_slugs = CUP_SLUGS_BY_LEAGUE.get(league_id_found, [])
    for cup_slug in cup_slugs:
        r = requests.get(f"{ESPN_BASE}/{cup_slug}/teams/{team_id}/schedule?season={season}")
        if r.status_code == 200 and r.json().get("events"):
            league_events += [(e, cup_slug) for e in r.json()["events"]]

    # Filter to finished matches only
    finished = []
    for e, slug in league_events:
        comp = e.get("competitions", [{}])[0]
        status = comp.get("status", {}).get("type", {}).get("name", "")
        if status != "STATUS_FULL_TIME":
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
        home = competitors[0]
        away = competitors[1]
        home_score = home.get("score", {})
        away_score = away.get("score", {})
        finished.append({
            "fixture_id": e["id"],
            "espn_slug": slug,
            "competition": SLUG_NAMES.get(slug, slug),
            "date": e["date"],
            "home": home["team"]["displayName"],
            "home_logo": home["team"].get("logos", [{}])[0].get("href", "") if home["team"].get("logos") else "",
            "away": away["team"]["displayName"],
            "away_logo": away["team"].get("logos", [{}])[0].get("href", "") if away["team"].get("logos") else "",
            "score": {
                "home": int(home_score.get("value", 0)) if isinstance(home_score, dict) else int(home_score or 0),
                "away": int(away_score.get("value", 0)) if isinstance(away_score, dict) else int(away_score or 0),
            }
        })

    finished.sort(key=lambda m: m["date"], reverse=True)
    # Deduplicate by fixture_id
    seen = set()
    deduped = []
    for m in finished:
        if m["fixture_id"] not in seen:
            seen.add(m["fixture_id"])
            deduped.append(m)

    total = len(deduped)
    page = deduped[offset:offset + limit]
    return {
        "matches": page,
        "hasMore": offset + limit < total,
        "total": total
    }


@router.get("/match/{fixture_id}")
async def get_match_analysis(fixture_id: str, slug: str = ""):
    # Check Neo4j cache first
    try:
        from config import driver
        import json as _json
        with driver.session() as session:
            cached = session.run(
                "MATCH (m:MatchAnalysis {espn_id: $id}) RETURN m",
                {"id": fixture_id}
            ).single()
            if cached:
                m = dict(cached["m"])
                return {
                    "match": f"{m['home_team']} vs {m['away_team']}",
                    "score": {"home": m["score_home"], "away": m["score_away"]},
                    "date": m.get("date", ""),
                    "homeTeam": m["home_team"],
                    "awayTeam": m["away_team"],
                    "homeLogo": m.get("home_logo", ""),
                    "awayLogo": m.get("away_logo", ""),
                    "analysis": m["analysis"],
                    "stats": _json.loads(m.get("stats_json", "{}")),
                    "lineups": _json.loads(m.get("lineups_json", "{}")),
                    "goals": _json.loads(m.get("goals_json", "[]")),
                    "cards": _json.loads(m.get("cards_json", "[]")),
                    "substitutions": [],
                    "dataNote": None,
                    "cached": True
                }
    except Exception:
        pass

    # If slug provided, try it directly first — much faster
    summary = None
    espn_slug = slug or "esp.1"  # default fallback

    if slug:
        r = requests.get(f"{ESPN_BASE}/{slug}/scoreboard/{fixture_id}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            comp = data.get("competitions", [{}])[0]
            if comp.get("competitors"):
                summary = data
                espn_slug = slug

    # Fallback: try all slugs concurrently
    if not summary:
        all_slugs = list(ESPN_LEAGUE_MAP.values()) + [
            "eng.fa", "eng.league_cup", "esp.copa_del_rey",
            "ita.coppa_italia", "ger.dfb_pokal", "fra.coupe_de_france",
            "uefa.europa", "uefa.europa.conf",
        ]
        async with httpx.AsyncClient() as client:
            tasks = [
                client.get(f"{ESPN_BASE}/{s}/scoreboard/{fixture_id}", timeout=10)
                for s in all_slugs
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(responses):
            if isinstance(r, Exception) or r.status_code != 200:
                continue
            data = r.json()
            if data.get("competitions", [{}])[0].get("competitors"):
                summary = data
                espn_slug = all_slugs[i]
                break

    if not summary:
        return {"error": "Match not found"}

    # Parse from scoreboard format
    comp = summary.get("competitions", [{}])[0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return {"error": "Match data incomplete"}

    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
    home_team = home_comp["team"]["displayName"]
    away_team = away_comp["team"]["displayName"]
    home_score = int(home_comp.get("score", 0) or 0)
    away_score = int(away_comp.get("score", 0) or 0)
    home_logo = home_comp["team"].get("logo", "")
    away_logo = away_comp["team"].get("logo", "")
    score = {"home": home_score, "away": away_score}
    match_date = comp.get("date", summary.get("date", ""))

    # Parse stats from scoreboard competitors
    stats = {}
    for c in competitors:
        tn = c.get("team", {}).get("displayName", "")
        stats[tn] = {s["name"]: s.get("displayValue", "—") for s in c.get("statistics", [])}

    # Map ESPN stat names to display labels
    STAT_LABEL_MAP = {
        "possessionPct": "Possession", "totalShots": "SHOTS",
        "shotsOnTarget": "ON GOAL", "wonCorners": "Corner Kicks",
        "foulsCommitted": "Fouls", "totalPasses": "Passes",
    }
    for tn in stats:
        mapped = {}
        for k, v in stats[tn].items():
            label = STAT_LABEL_MAP.get(k, k)
            mapped[label] = v
        stats[tn] = mapped

    # Goals and cards from details
    goals, cards = [], []
    home_id = str(home_comp.get("team", {}).get("id", ""))
    away_id = str(away_comp.get("team", {}).get("id", ""))
    for detail in comp.get("details", []):
        minute = detail.get("clock", {}).get("displayValue", "")
        athletes = detail.get("athletesInvolved", [])
        player = athletes[0].get("displayName", "") if athletes else ""
        team_id = str(detail.get("team", {}).get("id", ""))
        team_name = home_team if team_id == home_id else away_team
        if detail.get("scoringPlay"):
            d = "Own Goal" if detail.get("ownGoal") else ("Penalty" if detail.get("penaltyKick") else "Goal")
            goals.append({"minute": minute, "team": team_name, "player": player, "detail": d})
        elif detail.get("yellowCard"):
            cards.append({"minute": minute, "team": team_name, "player": player, "card": "Yellow Card"})
        elif detail.get("redCard"):
            cards.append({"minute": minute, "team": team_name, "player": player, "card": "Red Card"})

    lineups = {}
    subs = []
    commentary_block = "No detailed play data available."

    # Fetch detailed stats + plays concurrently
    core_base = f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{espn_slug}/events/{fixture_id}/competitions/{fixture_id}"
    home_team_id = home_comp.get("team", {}).get("id", "")
    away_team_id = away_comp.get("team", {}).get("id", "")

    async with httpx.AsyncClient() as client:
        r_home_stats, r_away_stats, r_plays, r_home_roster, r_away_roster, r_home_site_roster, r_away_site_roster = await asyncio.gather(
            client.get(f"{core_base}/competitors/{home_team_id}/statistics", timeout=8),
            client.get(f"{core_base}/competitors/{away_team_id}/statistics", timeout=8),
            client.get(f"{core_base}/plays?limit=300", timeout=8),
            client.get(f"{core_base}/competitors/{home_team_id}/roster", timeout=8),
            client.get(f"{core_base}/competitors/{away_team_id}/roster", timeout=8),
            client.get(f"{ESPN_BASE}/{espn_slug}/teams/{home_team_id}/roster", timeout=8),
            client.get(f"{ESPN_BASE}/{espn_slug}/teams/{away_team_id}/roster", timeout=8),
            return_exceptions=True
        )

    def parse_core_stats(r):
        if isinstance(r, Exception) or r.status_code != 200:
            return {}
        result = {}
        for cat in r.json().get("splits", {}).get("categories", []):
            for s in cat.get("stats", []):
                result[s["displayName"]] = s.get("displayValue", "—")
        return result

    detailed_home = parse_core_stats(r_home_stats)
    detailed_away = parse_core_stats(r_away_stats)

    # Merge detailed stats into stats dict
    if detailed_home:
        stats[home_team] = {**stats.get(home_team, {}), **detailed_home}
    if detailed_away:
        stats[away_team] = {**stats.get(away_team, {}), **detailed_away}

    # Parse rosters for lineups — cross-reference core roster (starter flags) with site roster (names)
    def parse_roster(r_core, r_site):
        if isinstance(r_core, Exception) or r_core.status_code != 200:
            return {"formation": "", "startXI": [], "coach": None}
        core_data = r_core.json()
        formation = core_data.get("formation", {}).get("summary", "")

        # Build id->name map from site roster
        id_to_name = {}
        if not isinstance(r_site, Exception) and r_site.status_code == 200:
            for a in r_site.json().get("athletes", []):
                id_to_name[str(a["id"])] = a.get("displayName", "")

        import re as _re

        # Collect $ref URLs for starters whose names we still need
        missing_refs = []

        starters = []
        for e in core_data.get("entries", []):
            if not e.get("starter"):
                continue

            # Try playerId first
            pid = str(e.get("playerId", ""))
            if pid and pid in id_to_name:
                starters.append(id_to_name[pid])
                continue

            # Extract ID from athlete $ref URL
            ref = e.get("athlete", {}).get("$ref", "")
            aid = ""
            if ref:
                m = _re.search(r"/athletes/(\d+)", ref)
                if m:
                    aid = m.group(1)

            if aid and aid in id_to_name:
                starters.append(id_to_name[aid])
            elif ref:
                # Queue for async resolution
                missing_refs.append((ref, len(starters)))
                starters.append(None)  # placeholder

        return {"formation": formation, "startXI": starters, "coach": None, "_missing_refs": missing_refs}

    lineups[home_team] = parse_roster(r_home_roster, r_home_site_roster)
    lineups[away_team] = parse_roster(r_away_roster, r_away_site_roster)

    # Resolve any players whose names couldn't be found via site roster
    async def resolve_missing(lineup: dict):
        missing = lineup.pop("_missing_refs", [])
        if not missing:
            lineup["startXI"] = [p for p in lineup["startXI"] if p is not None]
            return
        async with httpx.AsyncClient() as client:
            tasks = [client.get(ref, timeout=6) for ref, _ in missing]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        for (ref, idx), r in zip(missing, results):
            name = None
            if not isinstance(r, Exception) and r.status_code == 200:
                name = r.json().get("displayName") or r.json().get("fullName")
            lineup["startXI"][idx] = name
        lineup["startXI"] = [p for p in lineup["startXI"] if p is not None]

    await asyncio.gather(
        resolve_missing(lineups[home_team]),
        resolve_missing(lineups[away_team]),
    )
    commentary_lines = []
    KEEP_TYPES = {"goal","penalty---scored","own-goal","shot-on-target","shot-off-target",
                  "yellow-card","red-card","substitution","var"}
    if not isinstance(r_plays, Exception) and r_plays.status_code == 200:
        for play in r_plays.json().get("items", []):
            ptype = play.get("type", {}).get("type", "")
            text = play.get("text", "") or play.get("alternativeText", "")
            clock = play.get("clock", {}).get("displayValue", "")
            team_ref = play.get("team", {}).get("$ref", "")
            team_name = home_team if str(home_team_id) in team_ref else away_team if str(away_team_id) in team_ref else ""
            if ptype in KEEP_TYPES and text:
                commentary_lines.append(f"{clock} [{team_name}] {text}")
            if play.get("substitution"):
                subs.append({"minute": clock, "team": team_name, "detail": text})

    commentary_block = "\n".join(commentary_lines[:80]) if commentary_lines else "No detailed play data available."

    home_stats = stats.get(home_team, {})
    away_stats = stats.get(away_team, {})

    system_prompt = """You are an elite football analyst. Write a concise tactical match report in flowing prose."""

    prompt = f"""MATCH: {home_team} {home_score} – {away_score} {away_team} ({match_date[:10] if match_date else 'N/A'})

STATISTICS:
Possession: {home_stats.get('Possession %', home_stats.get('possessionPct', '—'))} vs {away_stats.get('Possession %', away_stats.get('possessionPct', '—'))}
Shots: {home_stats.get('Shots', home_stats.get('totalShots', '—'))} vs {away_stats.get('Shots', away_stats.get('totalShots', '—'))}
On Target: {home_stats.get('Shots on Target', home_stats.get('shotsOnTarget', '—'))} vs {away_stats.get('Shots on Target', away_stats.get('shotsOnTarget', '—'))}
Tackles Won: {home_stats.get('Tackles Won', home_stats.get('effectiveTackles', '—'))} vs {away_stats.get('Tackles Won', away_stats.get('effectiveTackles', '—'))}
Interceptions: {home_stats.get('Interceptions', '—')} vs {away_stats.get('Interceptions', '—')}
Corners: {home_stats.get('Corner Kicks', home_stats.get('wonCorners', '—'))} vs {away_stats.get('Corner Kicks', away_stats.get('wonCorners', '—'))}
Fouls: {home_stats.get('Fouls', home_stats.get('foulsCommitted', '—'))} vs {away_stats.get('Fouls', away_stats.get('foulsCommitted', '—'))}

GOALS: {chr(10).join(f"{g['minute']} {g['player']} ({g['team']}) — {g['detail']}" for g in goals) if goals else 'None'}
CARDS: {chr(10).join(f"{c['minute']} {c['player']} ({c['team']}) — {c['card']}" for c in cards) if cards else 'None'}

KEY EVENTS:
{commentary_block}

Write:
**Match Overview** — 3-4 bullets on flow and control
**Key Tactical Battles** — 2-3 bullets on patterns from the data
**Turning Points** — 2-3 bullets on moments that changed the game
**Verdict** — 1-2 sentences on why this result happened"""

    try:
        analysis = chat(prompt, system=system_prompt, max_tokens=1500)
    except Exception:
        analysis = "AI analysis unavailable."

    # Only cache if analysis is complete (has all 4 sections)
    required_sections = ["Match Overview", "Key Tactical Battles", "Turning Points", "Verdict"]
    is_complete = all(section in analysis for section in required_sections)

    if is_complete:
        try:
            from config import driver
            import json as _json
            with driver.session() as session:
                session.run("""
                    MERGE (m:MatchAnalysis {espn_id: $id})
                    SET m.analysis = $analysis,
                        m.home_team = $home,
                        m.away_team = $away,
                        m.home_logo = $home_logo,
                        m.away_logo = $away_logo,
                        m.score_home = $sh,
                        m.score_away = $sa,
                        m.date = $date,
                        m.goals_json = $goals,
                        m.cards_json = $cards,
                        m.stats_json = $stats,
                        m.lineups_json = $lineups,
                        m.cached_at = datetime()
                """, {
                    "id": fixture_id,
                    "analysis": analysis,
                    "home": home_team,
                    "away": away_team,
                    "home_logo": home_logo,
                    "away_logo": away_logo,
                    "sh": home_score,
                    "sa": away_score,
                    "date": match_date,
                    "goals": _json.dumps(goals),
                    "cards": _json.dumps(cards),
                    "stats": _json.dumps(stats),
                    "lineups": _json.dumps(lineups),
                })
        except Exception:
            pass

    data_note = None if (goals or stats) else "Detailed stats not available for this match."

    return {
        "match": f"{home_team} vs {away_team}",
        "score": score,
        "date": match_date,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeLogo": home_logo,
        "awayLogo": away_logo,
        "stats": stats,
        "lineups": lineups,
        "goals": goals,
        "cards": cards,
        "substitutions": subs,
        "analysis": analysis,
        "dataNote": data_note
    }
