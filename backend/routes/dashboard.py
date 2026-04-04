import os
import time
import requests
import asyncio
import httpx
import pandas as pd
from datetime import date
from fastapi import APIRouter
from fastapi.responses import Response
from config import API_KEY, driver
from llm import chat

router = APIRouter()

FD_HEADERS = {"X-Auth-Token": API_KEY}

# Simple in-memory backend cache — avoids hammering football-data.org
_cache: dict = {}
_CACHE_TTL = 10 * 60  # 10 minutes

def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None

def _cache_set(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}

# Load players CSV once for photo lookups
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "players.csv")
try:
    _PLAYERS_DF = pd.read_csv(_CSV_PATH, usecols=["name", "image_url"])
except Exception:
    _PLAYERS_DF = None

def _get_player_image_url(name: str) -> str | None:
    if _PLAYERS_DF is None:
        return None
    # Exact match first
    match = _PLAYERS_DF[_PLAYERS_DF["name"].str.lower() == name.lower()]
    if match.empty:
        # Full name contains match — require all words to be present
        words = name.lower().split()
        mask = _PLAYERS_DF["name"].str.lower().apply(lambda n: all(w in n for w in words))
        match = _PLAYERS_DF[mask]
    if not match.empty:
        url = match.iloc[0]["image_url"]
        if isinstance(url, str) and "default" not in url:
            return url
    return None

TOP5_LEAGUES = [
    {"code": "PL",  "name": "Premier League"},
    {"code": "PD",  "name": "La Liga"},
    {"code": "SA",  "name": "Serie A"},
    {"code": "BL1", "name": "Bundesliga"},
    {"code": "FL1", "name": "Ligue 1"},
]

# Players to rotate through for spotlight (index by day of year % len)
SPOTLIGHT_PLAYERS = [
    {"name": "Kylian Mbappé", "club": "Real Madrid", "nationality": "France", "position": "Forward"},
    {"name": "Erling Haaland", "club": "Manchester City", "nationality": "Norway", "position": "Striker"},
    {"name": "Bukayo Saka", "club": "Arsenal", "nationality": "England", "position": "Winger"},
    {"name": "Vinicius Junior", "club": "Real Madrid", "nationality": "Brazil", "position": "Winger"},
    {"name": "Mohamed Salah", "club": "Liverpool", "nationality": "Egypt", "position": "Winger"},
    {"name": "Jude Bellingham", "club": "Real Madrid", "nationality": "England", "position": "Midfielder"},
    {"name": "Harry Kane", "club": "Bayern Munich", "nationality": "England", "position": "Striker"},
]


@router.get("/dashboard/recent-matches")
async def get_recent_matches():
    cached = _cache_get("recent-matches")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                f"https://api.football-data.org/v4/competitions/{league['code']}/matches?status=FINISHED&limit=3",
                headers=FD_HEADERS, timeout=10
            )
            for league in TOP5_LEAGUES
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_matches = []
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        league = TOP5_LEAGUES[i]
        matches = r.json().get("matches", [])
        matches.sort(key=lambda m: m["utcDate"], reverse=True)
        for m in matches[:3]:
            all_matches.append({
                "date": m["utcDate"],
                "league": league["name"],
                "home": m["homeTeam"]["name"],
                "home_logo": m["homeTeam"].get("crest", ""),
                "away": m["awayTeam"]["name"],
                "away_logo": m["awayTeam"].get("crest", ""),
                "score": {
                    "home": m["score"]["fullTime"]["home"],
                    "away": m["score"]["fullTime"]["away"]
                }
            })

    all_matches.sort(key=lambda m: m["date"], reverse=True)
    result = all_matches[:6]
    _cache_set("recent-matches", result)
    return result


@router.get("/dashboard/in-form")
async def get_in_form_teams():
    """Get most in-form teams across top 5 leagues — fetched concurrently."""
    cached = _cache_get("in-form")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                f"https://api.football-data.org/v4/competitions/{league['code']}/matches?status=FINISHED&limit=20",
                headers=FD_HEADERS, timeout=10
            )
            for league in TOP5_LEAGUES
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_scored = []
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        league = TOP5_LEAGUES[i]
        matches = r.json().get("matches", [])
        team_results: dict = {}
        for m in reversed(matches):
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            winner = m["score"].get("winner")
            for team in [home, away]:
                if team not in team_results:
                    team_results[team] = []
                if len(team_results[team]) < 5:
                    if (winner == "HOME_TEAM" and team == home) or (winner == "AWAY_TEAM" and team == away):
                        team_results[team].append("W")
                    elif winner == "DRAW":
                        team_results[team].append("D")
                    else:
                        team_results[team].append("L")

        for team, results in team_results.items():
            if len(results) >= 3:
                pts = sum(3 if rv == "W" else 1 if rv == "D" else 0 for rv in results)
                all_scored.append({"team": team, "league": league["name"], "form": "".join(results), "points": pts})

    all_scored.sort(key=lambda x: x["points"], reverse=True)
    result = all_scored[:5]
    _cache_set("in-form", result)
    return result


@router.get("/dashboard/best-defense")
@router.get("/dashboard/best-defense")
async def get_best_defense():
    cached = _cache_get("best-defense")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"https://api.football-data.org/v4/competitions/{league['code']}/standings",
                      headers=FD_HEADERS, timeout=10)
            for league in TOP5_LEAGUES
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_teams = []
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        standings = r.json().get("standings", [])
        total = next((s for s in standings if s["type"] == "TOTAL"), None)
        if not total:
            continue
        for t in total["table"]:
            if t["playedGames"] > 0:
                all_teams.append({
                    "team": t["team"]["name"],
                    "league": TOP5_LEAGUES[i]["name"],
                    "goalsAgainst": t["goalsAgainst"],
                    "played": t["playedGames"]
                })

    all_teams = [t for t in all_teams if t["played"] > 0]
    all_teams.sort(key=lambda x: x["goalsAgainst"])
    result = all_teams[:5]
    _cache_set("best-defense", result)
    return result


@router.get("/dashboard/best-offense")
async def get_best_offense():
    cached = _cache_get("best-offense")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"https://api.football-data.org/v4/competitions/{league['code']}/standings",
                      headers=FD_HEADERS, timeout=10)
            for league in TOP5_LEAGUES
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_teams = []
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        standings = r.json().get("standings", [])
        total = next((s for s in standings if s["type"] == "TOTAL"), None)
        if not total:
            continue
        for t in total["table"]:
            if t["playedGames"] > 0:
                all_teams.append({
                    "team": t["team"]["name"],
                    "league": TOP5_LEAGUES[i]["name"],
                    "goalsFor": t["goalsFor"],
                    "played": t["playedGames"]
                })

    all_teams.sort(key=lambda x: x["goalsFor"], reverse=True)
    result = all_teams[:5]
    _cache_set("best-offense", result)
    return result



def get_diverse_squad():
    """Get most diverse squads from Neo4j."""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                RETURN c.name AS team, count(DISTINCT p.nationality) AS nationalities
                ORDER BY nationalities DESC LIMIT 3
            """)
            return [{"team": r["team"], "nationalities": r["nationalities"]} for r in result]
    except Exception:
        return []


@router.get("/dashboard/spotlight")
def get_player_spotlight():
    """Return today's featured player with AI-generated summary."""
    day_index = date.today().timetuple().tm_yday % len(SPOTLIGHT_PLAYERS)
    player = SPOTLIGHT_PLAYERS[day_index]

    # AI summary from Groq
    prompt = f"""Give a concise football scouting report for {player['name']} ({player['position']}, {player['club']}).
Cover:
1. Playstyle (2-3 sentences)
2. Key strengths (3 bullet points)
3. Weaknesses (2 bullet points)
Keep it factual and concise."""

    summary = chat(prompt, system="You are a football scout. Be factual, concise, no fluff.", max_tokens=400)

    return {
        "name": player["name"],
        "club": player["club"],
        "nationality": player["nationality"],
        "position": player["position"],
        "photo": f"http://localhost:8000/dashboard/player-photo?name={requests.utils.quote(player['name'])}",
        "summary": summary,
    }


@router.get("/dashboard/player-photo")
def proxy_player_photo(name: str):
    """Proxy player image from Transfermarkt to bypass hotlink protection."""
    url = _get_player_image_url(name)
    if not url:
        return Response(status_code=404)
    try:
        r = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.transfermarkt.com/"
        })
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "image/jpeg")
            return Response(content=r.content, media_type=content_type)
    except Exception:
        pass
    return Response(status_code=404)

ESPN_LEAGUE_SLUGS = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "uefa.champions"]
ESPN_NEWS_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

@router.get("/dashboard/news")
def get_news():
    cached = _cache_get("news")
    if cached is not None:
        return cached
    articles = []
    seen = set()
    for slug in ESPN_LEAGUE_SLUGS:
        try:
            r = requests.get(f"{ESPN_NEWS_BASE}/{slug}/news", timeout=5)
            if r.status_code != 200:
                continue
            for a in r.json().get("articles", []):
                headline = a.get("headline", "")
                if not headline or headline in seen:
                    continue
                seen.add(headline)
                image = None
                for img in a.get("images", []):
                    if img.get("url"):
                        image = img["url"]
                        break
                link = None
                links = a.get("links", {})
                if isinstance(links, dict):
                    link = links.get("web", {}).get("href")
                elif isinstance(links, list):
                    for l in links:
                        if l.get("rel") and "web" in l.get("rel", []):
                            link = l.get("href")
                            break
                articles.append({
                    "headline": headline,
                    "description": a.get("description", ""),
                    "published": a.get("published", ""),
                    "image": image,
                    "link": link,
                })
        except Exception:
            continue
    _cache_set("news", articles)
    return articles

LIVE_SLUGS = [
    "eng.1", "eng.fa", "eng.league_cup",          # Premier League + FA Cup + League Cup
    "esp.1", "esp.copa_del_rey",                   # La Liga + Copa del Rey
    "ita.1", "ita.coppa_italia",                   # Serie A + Coppa Italia
    "ger.1", "ger.dfb_pokal",                      # Bundesliga + DFB Pokal
    "fra.1", "fra.coupe_de_france",                # Ligue 1 + Coupe de France
    "uefa.champions", "uefa.europa", "uefa.europa.conf",
]
LIVE_SLUG_NAMES = {
    "eng.1": "Premier League", "eng.fa": "FA Cup", "eng.league_cup": "League Cup",
    "esp.1": "La Liga", "esp.copa_del_rey": "Copa del Rey",
    "ita.1": "Serie A", "ita.coppa_italia": "Coppa Italia",
    "ger.1": "Bundesliga", "ger.dfb_pokal": "DFB Pokal",
    "fra.1": "Ligue 1", "fra.coupe_de_france": "Coupe de France",
    "uefa.champions": "Champions League", "uefa.europa": "Europa League",
    "uefa.europa.conf": "Conference League",
}

@router.get("/dashboard/live-scores")
def get_live_scores():
    results = []
    for slug in LIVE_SLUGS:
        try:
            r = requests.get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard",
                timeout=6
            )
            if r.status_code != 200:
                continue
            for event in r.json().get("events", []):
                comp = event.get("competitions", [{}])[0]
                status = comp.get("status", {})
                state = status.get("type", {}).get("state", "")  # pre / in / post
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue

                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                # Stats
                stats_raw = {}
                for c in competitors:
                    team_name = c.get("team", {}).get("displayName", "")
                    stats_raw[team_name] = {s["name"]: s.get("displayValue", "—") for s in c.get("statistics", [])}

                # Extract goal scorers from details
                goals: dict = {"home": [], "away": []}
                home_id = str(home.get("team", {}).get("id", ""))
                away_id = str(away.get("team", {}).get("id", ""))
                for detail in comp.get("details", []):
                    if not detail.get("scoringPlay"):
                        continue
                    minute = detail.get("clock", {}).get("displayValue", "")
                    athletes = detail.get("athletesInvolved", [])
                    scorer = athletes[0].get("shortName", "") if athletes else ""
                    own_goal = detail.get("ownGoal", False)
                    penalty = detail.get("penaltyKick", False)
                    team_id = str(detail.get("team", {}).get("id", ""))
                    label = f"{scorer} {minute}"
                    if own_goal: label += " (OG)"
                    if penalty: label += " (P)"
                    if team_id == home_id:
                        goals["home"].append(label)
                    elif team_id == away_id:
                        goals["away"].append(label)

                results.append({
                    "id": event.get("id"),
                    "league": LIVE_SLUG_NAMES.get(slug, slug),
                    "state": state,
                    "clock": status.get("displayClock", ""),
                    "detail": status.get("type", {}).get("detail", ""),
                    "home": {
                        "name": home.get("team", {}).get("displayName", ""),
                        "shortName": home.get("team", {}).get("abbreviation", ""),
                        "logo": home.get("team", {}).get("logo", ""),
                        "score": home.get("score", "0"),
                        "winner": home.get("winner", False),
                        "goals": goals["home"],
                    },
                    "away": {
                        "name": away.get("team", {}).get("displayName", ""),
                        "shortName": away.get("team", {}).get("abbreviation", ""),
                        "logo": away.get("team", {}).get("logo", ""),
                        "score": away.get("score", "0"),
                        "winner": away.get("winner", False),
                        "goals": goals["away"],
                    },
                    "venue": comp.get("venue", {}).get("fullName", ""),
                    "stats": stats_raw,
                })
        except Exception:
            continue
    return results
