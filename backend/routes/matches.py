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


@router.get("/team-matches/{team_id}")
def get_team_matches(team_id: int, season: int = 2024, limit: int = 5, offset: int = 0):
    # Find which league this team belongs to by trying each
    espn_slug = None
    for slug in ESPN_LEAGUE_MAP.values():
        r = requests.get(f"{ESPN_BASE}/{slug}/teams/{team_id}/schedule?season={season}")
        if r.status_code == 200 and r.json().get("events"):
            espn_slug = slug
            events = r.json()["events"]
            break

    if not espn_slug:
        return {"matches": [], "hasMore": False}

    # Filter to finished matches only, sort by date desc
    finished = []
    for e in events:
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
            "espn_slug": espn_slug,
            "date": e["date"],
            "round": e.get("season", {}).get("slug", ""),
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
    total = len(finished)
    page = finished[offset:offset + limit]
    return {
        "matches": page,
        "hasMore": offset + limit < total,
        "total": total
    }


@router.get("/match/{fixture_id}")
async def get_match_analysis(fixture_id: str):
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

    # Try all slugs concurrently
    all_slugs = list(ESPN_LEAGUE_MAP.values()) + [
        "eng.fa", "eng.league_cup", "esp.copa_del_rey",
        "ita.coppa_italia", "ger.dfb_pokal", "fra.coupe_de_france",
        "uefa.europa", "uefa.europa.conf",
    ]

    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{ESPN_BASE}/{slug}/summary?event={fixture_id}", timeout=10)
            for slug in all_slugs
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    summary = None
    for r in responses:
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        data = r.json()
        if data.get("header"):
            summary = data
            break

    if not summary:
        return {"error": "Match not found"}

    header = summary.get("header", {})
    competitions = header.get("competitions", [{}])[0]
    competitors = competitions.get("competitors", [])
    if len(competitors) < 2:
        return {"error": "Match data incomplete"}

    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
    home_team = home_comp["team"]["displayName"]
    away_team = away_comp["team"]["displayName"]
    home_score = int(home_comp.get("score", 0) or 0)
    away_score = int(away_comp.get("score", 0) or 0)
    home_logo = home_comp["team"].get("logos", [{}])[0].get("href", "") if home_comp["team"].get("logos") else ""
    away_logo = away_comp["team"].get("logos", [{}])[0].get("href", "") if away_comp["team"].get("logos") else ""
    score = {"home": home_score, "away": away_score}
    match_date = competitions.get("date", "")

    # Parse stats
    stats = {}
    for team_data in summary.get("boxscore", {}).get("teams", []):
        tn = team_data.get("team", {}).get("displayName", "")
        stats[tn] = {s["label"]: s["displayValue"] for s in team_data.get("statistics", [])}

    # Parse lineups + fetch coach from roster endpoint
    lineups = {}
    for roster in summary.get("rosters", []):
        tn = roster.get("team", {}).get("displayName", "")
        team_id = roster.get("team", {}).get("id", "")
        formation = roster.get("formation", "")
        starters = [p for p in roster.get("roster", []) if p.get("starter")]

        # Fetch coach from football-data.org using team name search
        coach_name = None
        if tn:
            from utils import get_team_id
            fd_team_id = get_team_id(tn)
            if fd_team_id:
                coach_res = requests.get(
                    f"https://api.football-data.org/v4/teams/{fd_team_id}",
                    headers=FD_HEADERS
                )
                if coach_res.status_code == 200:
                    coach_data = coach_res.json().get("coach", {})
                    if coach_data:
                        coach_name = coach_data.get("name") or f"{coach_data.get('firstName', '')} {coach_data.get('lastName', '')}".strip()

        lineups[tn] = {
            "formation": formation,
            "startXI": [p["athlete"]["displayName"] for p in starters],
            "coach": coach_name
        }

    # Fetch ALL plays for commentary + goals
    goals, cards, subs = [], [], []
    commentary_lines = []

    # Event types to KEEP for commentary (meaningful football events)
    KEEP_TYPES = {
        "goal", "penalty---scored", "own-goal",
        "shot-on-target", "shot-off-target", "shot-hit-woodwork",
        "save", "yellow-card", "red-card",
        "corner-kick", "free-kick", "offside",
        "substitution", "foul", "var"
    }
    # Types to SKIP (noise)
    SKIP_TYPES = {
        "kickoff", "halftime", "start-2nd-half", "end-period",
        "assists-shot", "throw-in", "goal-kick"
    }

    plays_res = requests.get(
        f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{espn_slug}/events/{fixture_id}/competitions/{fixture_id}/plays?limit=300"
    )
    if plays_res.status_code == 200:
        for play in plays_res.json().get("items", []):
            ptype = play.get("type", {}).get("type", "")
            text = play.get("text", "")
            clock = play.get("clock", {}).get("displayValue", "")
            team_name = play.get("team", {}).get("displayName", "")
            short = play.get("shortText", "")

            if ptype in SKIP_TYPES or not text:
                continue

            # Extract goals
            if ptype in ("goal", "penalty---scored"):
                player = short.replace(" Goal", "").replace(" (OG)", "").strip() if short else ""
                if not player and "." in text:
                    after = text.split(".", 1)[1].strip()
                    player = after.split("(")[0].strip() if "(" in after else after.split(" ")[0]
                goals.append({"minute": clock, "team": team_name, "player": player, "detail": "Goal"})
            elif ptype == "own-goal":
                player = short.replace(" Own Goal", "").strip() if short else text.split(",")[0].replace("Own Goal by ", "").strip()
                goals.append({"minute": clock, "team": team_name, "player": player, "detail": "Own Goal"})
            elif ptype in ("yellow-card", "red-card"):
                cards.append({"minute": clock, "team": team_name, "player": text.split("(")[0].strip(), "card": "Yellow Card" if ptype == "yellow-card" else "Red Card"})
            elif ptype == "substitution":
                subs.append({"minute": clock, "team": team_name, "detail": text})

            # Build commentary for LLM — keep meaningful events
            if ptype in KEEP_TYPES and text and "assists shot" not in text.lower():
                team_label = f"[{team_name}]" if team_name else ""
                commentary_lines.append(f"{clock} {team_label} {text}")

    home_stats = stats.get(home_team, {})
    away_stats = stats.get(away_team, {})

    # Build starters string with positions
    def format_lineup(team_name):
        roster_data = next((r for r in summary.get("rosters", []) if r.get("team", {}).get("displayName") == team_name), {})
        starters = [p for p in roster_data.get("roster", []) if p.get("starter")]
        return ", ".join(
            f"{p['athlete']['displayName']} ({p.get('position', {}).get('abbreviation', '?')})"
            for p in starters
        )

    home_xi = format_lineup(home_team)
    away_xi = format_lineup(away_team)

    # Build commentary block — cap at 80 most meaningful lines to stay within token budget
    commentary_block = "\n".join(commentary_lines[:80]) if commentary_lines else "No detailed play data available."

    system_prompt = """You are an elite football analyst writing a match report.
CRITICAL RULE: You may ONLY describe actions that are explicitly stated in the PLAY-BY-PLAY EVENTS section.
If the play-by-play says "right footed shot from the centre of the box" — use that exact description naturally in your sentence WITHOUT quotation marks. Do NOT say "header" if the data says "shot". Do NOT invent assists, body parts, or descriptions not in the data.
Write in flowing prose — never use quotation marks around play descriptions.
Use football terminology naturally but stay strictly within what the data shows."""

    prompt = f"""MATCH REPORT REQUEST

{home_team} {home_score} – {away_score} {away_team}
Date: {match_date[:10] if match_date else 'N/A'}

=== FORMATIONS & LINEUPS ===
{home_team} ({lineups.get(home_team, {}).get('formation', 'N/A')}): {home_xi}
{away_team} ({lineups.get(away_team, {}).get('formation', 'N/A')}): {away_xi}

=== MATCH STATISTICS ===
                        {home_team:<30} {away_team}
Possession:             {home_stats.get('Possession', '—'):<30} {away_stats.get('Possession', '—')}
Shots:                  {home_stats.get('SHOTS', '—'):<30} {away_stats.get('SHOTS', '—')}
Shots on Target:        {home_stats.get('ON GOAL', '—'):<30} {away_stats.get('ON GOAL', '—')}
Passes:                 {home_stats.get('Passes', '—'):<30} {away_stats.get('Passes', '—')}
Pass Accuracy:          {home_stats.get('Pass Completion %', '—'):<30} {away_stats.get('Pass Completion %', '—')}
Corners:                {home_stats.get('Corner Kicks', '—'):<30} {away_stats.get('Corner Kicks', '—')}
Fouls:                  {home_stats.get('Fouls', '—'):<30} {away_stats.get('Fouls', '—')}
Tackles:                {home_stats.get('Effective Tackles', '—'):<30} {away_stats.get('Effective Tackles', '—')}
Crosses:                {home_stats.get('Accurate Crosses', '—'):<30} {away_stats.get('Accurate Crosses', '—')}

=== GOALS ===
{chr(10).join(f"{g['minute']} {g['player']} ({g['team']}) — {g['detail']}" for g in goals) if goals else 'No goals'}

=== CARDS ===
{chr(10).join(f"{c['minute']} {c['player']} ({c['team']}) — {c['card']}" for c in cards) if cards else 'No cards'}

=== PLAY-BY-PLAY EVENTS ===
{commentary_block}

=== YOUR TASK ===
IMPORTANT: For every specific action you describe (shots, goals, assists, saves), use the EXACT wording from the PLAY-BY-PLAY EVENTS above. Do not paraphrase shot types — if it says "right footed shot", say "right footed shot", not "header" or "volley".

Write a tactical match analysis with these sections:
**Match Overview** — 3-4 bullet points on the overall flow, possession patterns, and which team controlled the game
**Key Tactical Battles** — 2-3 bullet points describing patterns you can see in the play-by-play data (e.g. which zones had most fouls, which team won more corners, pressing patterns visible from foul locations). Do NOT describe player roles or positions unless the play-by-play explicitly states them
**Turning Points** — 2-3 bullet points ONLY on moments that changed the tactical dynamic of the match (e.g. a red card forcing a team to sit deeper, a substitution that changed the game, a goal that forced the losing team to abandon their defensive shape and chase the game). Do NOT list every goal — only moments that caused a tactical shift
**Verdict** — 1-2 sentences on why this result happened

Rules:
- Every claim must be supported by the play-by-play data above
- Use player names from the lineups when describing actions
- Be specific about minutes, zones, and patterns you can see in the data
- Do NOT use ### headers, use **bold** headings only"""

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
