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

def _cache_set(key: str, data, ttl: int = _CACHE_TTL):
    _cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}

def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < entry.get("ttl", _CACHE_TTL):
        return entry["data"]
    return None

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


ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_SLUGS = [
    {"slug": "eng.1", "name": "Premier League"},
    {"slug": "esp.1", "name": "La Liga"},
    {"slug": "ita.1", "name": "Serie A"},
    {"slug": "ger.1", "name": "Bundesliga"},
    {"slug": "fra.1", "name": "Ligue 1"},
    {"slug": "eng.fa", "name": "FA Cup"},
    {"slug": "eng.league_cup", "name": "League Cup"},
    {"slug": "esp.copa_del_rey", "name": "Copa del Rey"},
    {"slug": "ita.coppa_italia", "name": "Coppa Italia"},
    {"slug": "ger.dfb_pokal", "name": "DFB Pokal"},
    {"slug": "fra.coupe_de_france", "name": "Coupe de France"},
    {"slug": "uefa.champions", "name": "Champions League"},
    {"slug": "uefa.europa", "name": "Europa League"},
    {"slug": "uefa.europa.conf", "name": "Conference League"},
]

@router.get("/dashboard/debug-fd")
async def debug_fd():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.football-data.org/v4/competitions/PL/standings",
            headers=FD_HEADERS, timeout=10
        )
    return {"status": r.status_code, "body": r.text[:500]}


ESPN_WEB_BASE = "https://site.web.api.espn.com/apis/v2/sports/soccer"
ESPN_STANDINGS_SLUGS = [
    {"slug": "eng.1", "name": "Premier League"},
    {"slug": "esp.1", "name": "La Liga"},
    {"slug": "ita.1", "name": "Serie A"},
    {"slug": "ger.1", "name": "Bundesliga"},
    {"slug": "fra.1", "name": "Ligue 1"},
]

async def _fetch_all_standings():
    cached = _cache_get("espn-standings")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{ESPN_WEB_BASE}/{l['slug']}/standings", timeout=10)
            for l in ESPN_STANDINGS_SLUGS
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    result = []
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            result.append(None)
            continue
        entries = []
        for child in r.json().get("children", []):
            entries += child.get("standings", {}).get("entries", [])
        result.append(entries if entries else None)
    _cache_set("espn-standings", result, ttl=12 * 60 * 60)
    return result


BIG_CLUBS = {
    "manchester city", "liverpool", "arsenal", "chelsea", "manchester united",
    "tottenham hotspur", "newcastle united", "aston villa",
    "real madrid", "barcelona", "atletico madrid",
    "bayern munich", "borussia dortmund", "bayer leverkusen",
    "juventus", "ac milan", "inter milan", "napoli",
    "paris saint-germain", "marseille",
    "ajax", "porto", "benfica",
}

def _match_popularity(m: dict) -> int:
    home = m["home"].lower()
    away = m["away"].lower()
    score = 0
    for club in BIG_CLUBS:
        if club in home: score += 1
        if club in away: score += 1
    # Bonus for cup/European matches between big clubs
    if score >= 2:
        score += 1
    return score


@router.get("/dashboard/recent-matches")
async def get_recent_matches():
    cached = _cache_get("recent-matches")
    if cached is not None:
        return cached

    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc)
    # Build date strings for last 7 days to query ESPN with a date range
    dates = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 8)]
    date_range = f"{dates[-1]}-{dates[0]}"  # e.g. 20260403-20260409

    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{ESPN_BASE}/{l['slug']}/scoreboard", params={"dates": date_range}, timeout=10)
            for l in ESPN_SLUGS
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_matches = []
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        league_name = ESPN_SLUGS[i]["name"]
        for event in r.json().get("events", []):
            comp = event.get("competitions", [{}])[0]
            status = comp.get("status", {}).get("type", {}).get("state", "")
            if status != "post":
                continue
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            home_id = str(home.get("team", {}).get("id", ""))
            away_id = str(away.get("team", {}).get("id", ""))

            goals = {"home": [], "away": []}
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

            all_matches.append({
                "date": event.get("date", ""),
                "league": league_name,
                "home": home.get("team", {}).get("displayName", ""),
                "home_logo": home.get("team", {}).get("logo", ""),
                "home_goals": goals["home"],
                "away": away.get("team", {}).get("displayName", ""),
                "away_logo": away.get("team", {}).get("logo", ""),
                "away_goals": goals["away"],
                "score": {
                    "home": home.get("score", "0"),
                    "away": away.get("score", "0"),
                }
            })

    all_matches.sort(key=lambda m: (_match_popularity(m), m["date"]), reverse=True)
    result = all_matches[:6]
    _cache_set("recent-matches", result)
    return result


@router.get("/dashboard/in-form")
async def get_in_form_teams():
    cached = _cache_get("in-form")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{ESPN_BASE}/{l['slug']}/scoreboard", timeout=10)
            for l in ESPN_SLUGS
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    team_form: dict = {}
    for i, r in enumerate(responses):
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        league_name = ESPN_SLUGS[i]["name"]
        for event in r.json().get("events", []):
            comp = event.get("competitions", [{}])[0]
            for c in comp.get("competitors", []):
                name = c.get("team", {}).get("displayName", "")
                form = c.get("form", "")  # e.g. "LWLWW"
                if name and form and name not in team_form:
                    team_form[name] = {"league": league_name, "form": form[-5:]}

    all_scored = []
    for team, v in team_form.items():
        form = v["form"]
        if len(form) < 3:
            continue
        pts = sum(3 if r == "W" else 1 if r == "D" else 0 for r in form)
        all_scored.append({"team": team, "league": v["league"], "form": form, "points": pts})

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
    standings = await _fetch_all_standings()
    all_teams = []
    for i, entries in enumerate(standings):
        if not entries:
            continue
        league_name = ESPN_STANDINGS_SLUGS[i]["name"]
        for entry in entries:
            team_name = entry.get("team", {}).get("displayName", "")
            ga = int(next((s.get("value", 0) for s in entry.get("stats", []) if s["name"] == "pointsAgainst"), 0) or 0)
            gp = int(next((s.get("value", 0) for s in entry.get("stats", []) if s["name"] == "gamesPlayed"), 0) or 0)
            if gp > 0:
                all_teams.append({"team": team_name, "league": league_name, "goalsAgainst": ga})
    all_teams.sort(key=lambda x: x["goalsAgainst"])
    result = all_teams[:5]
    _cache_set("best-defense", result)
    return result


@router.get("/dashboard/best-offense")
async def get_best_offense():
    cached = _cache_get("best-offense")
    if cached is not None:
        return cached
    standings = await _fetch_all_standings()
    all_teams = []
    for i, entries in enumerate(standings):
        if not entries:
            continue
        league_name = ESPN_STANDINGS_SLUGS[i]["name"]
        for entry in entries:
            team_name = entry.get("team", {}).get("displayName", "")
            gf = int(next((s.get("value", 0) for s in entry.get("stats", []) if s["name"] == "pointsFor"), 0) or 0)
            gp = int(next((s.get("value", 0) for s in entry.get("stats", []) if s["name"] == "gamesPlayed"), 0) or 0)
            if gp > 0:
                all_teams.append({"team": team_name, "league": league_name, "goalsFor": gf})
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
async def get_live_scores():
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    date_range = f"{yesterday}-{today}"

    results = []
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard",
                params={"dates": date_range},
                timeout=6
            )
            for slug in LIVE_SLUGS
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for idx, r in enumerate(responses):
        slug = LIVE_SLUGS[idx]
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        try:
            for event in r.json().get("events", []):
                comp = event.get("competitions", [{}])[0]
                status = comp.get("status", {})
                state = status.get("type", {}).get("state", "")
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue

                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                stats_raw = {}
                for c in competitors:
                    team_name = c.get("team", {}).get("displayName", "")
                    stats_raw[team_name] = {s["name"]: s.get("displayValue", "—") for s in c.get("statistics", [])}

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
