import requests
from fastapi import APIRouter
from config import API_KEY, API_FOOTBALL_KEY, driver
from utils import get_team_id
from llm import chat

router = APIRouter()

# Top leagues to search across for player lookup
SEARCH_LEAGUES = [39, 140, 135, 78, 61, 307, 253, 848, 2, 3]
# PL, La Liga, Serie A, Bundesliga, Ligue 1, Saudi Pro League, MLS, Champions League, World Cup, Euro

# Known player name → football-data.org person ID (kept for reference, not used for stats)
KNOWN_PLAYER_IDS = {
    "mbappe": "kylian mbappe",
    "ronaldo": "cristiano ronaldo",
    "messi": "lionel messi",
    "haaland": "erling haaland",
    "salah": "mohamed salah",
    "de bruyne": "kevin de bruyne",
    "benzema": "karim benzema",
    "lewandowski": "robert lewandowski",
    "vinicius": "vinicius jr",
    "bellingham": "jude bellingham",
    "saka": "bukayo saka",
    "kane": "harry kane",
}


def analyze_query(query: str):
    q = query.lower().strip()

    api_keywords = ["squad", "roster", "lineup", "players in", "team players", "premier league teams", "show teams"]
    graph_keywords = ["who plays for", "plays for", "playing for"]
    stats_keywords = ["stats", "statistics", "performance", "profile", "info", "details", "age of", "nationality of", "position of", "transfer history", "trophies"]

    # Alias map: user shorthand -> canonical club name used in the graph
    CLUB_ALIASES = {
        # Real Madrid
        "real": "real madrid", "rma": "real madrid", "rm": "real madrid",
        # Barcelona
        "barca": "barcelona", "fcb": "barcelona", "blaugrana": "barcelona",
        # Manchester City
        "man city": "manchester city", "mcfc": "manchester city", "city": "manchester city",
        # Manchester United
        "man united": "manchester united", "man utd": "manchester united", "mufc": "manchester united", "united": "manchester united",
        # Tottenham
        "spurs": "tottenham", "thfc": "tottenham",
        # PSG
        "paris": "psg", "paris saint-germain": "psg", "paris saint germain": "psg", "paris sg": "psg",
        # Bayern Munich
        "bayern": "bayern munich", "fcb münchen": "bayern munich", "fcbayern": "bayern munich",
        # Borussia Dortmund
        "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
        # Atletico Madrid
        "atletico": "atletico madrid", "atleti": "atletico madrid",
        # Juventus
        "juve": "juventus",
        # AC Milan
        "rossoneri": "ac milan",
        # Inter Milan
        "nerazzurri": "inter milan",
        # Liverpool
        "lfc": "liverpool", "the reds": "liverpool",
        # Arsenal
        "the gunners": "arsenal", "afc": "arsenal",
        # Chelsea
        "the blues": "chelsea", "cfc": "chelsea",
        # Newcastle
        "newcastle united": "newcastle", "nufc": "newcastle", "newcastle utd": "newcastle",
        # Aston Villa
        "villa": "aston villa", "avfc": "aston villa",
        # West Ham
        "west ham united": "west ham", "hammers": "west ham", "whufc": "west ham",
        # Bayer Leverkusen
        "leverkusen": "bayer leverkusen",
        # RB Leipzig
        "leipzig": "rb leipzig",
        # Sporting CP
        "sporting": "sporting cp",
        # Borussia Monchengladbach
        "gladbach": "borussia monchengladbach",
        # Eintracht Frankfurt
        "frankfurt": "eintracht frankfurt",
        # Al Nassr
        "nassr": "al nassr",
        # Al Hilal
        "hilal": "al hilal",
    }

    # Normalize aliases in query before any matching
    # Sort by length descending so longer aliases match first (e.g. "man city" before "city")
    q_normalized = q
    for alias, canonical in sorted(CLUB_ALIASES.items(), key=lambda x: -len(x[0])):
        import re
        # Only replace whole-word matches to avoid "inter" matching inside "inter miami"
        q_normalized = re.sub(r'\b' + re.escape(alias) + r'\b', canonical, q_normalized)

    known_clubs = [
        # Premier League
        "arsenal", "chelsea", "liverpool", "manchester city", "manchester united",
        "tottenham", "newcastle", "aston villa", "west ham", "brighton",
        "everton", "fulham", "brentford", "crystal palace", "wolves",
        "nottingham forest", "bournemouth", "burnley", "luton", "sheffield",
        "leicester", "leeds", "southampton",
        # La Liga
        "barcelona", "real madrid", "atletico madrid", "sevilla", "valencia",
        "villarreal", "real sociedad", "athletic bilbao", "real betis",
        # Serie A
        "juventus", "ac milan", "inter milan", "napoli", "as roma", "lazio",
        "atalanta", "fiorentina", "torino",
        # Bundesliga
        "bayern munich", "borussia dortmund", "rb leipzig", "bayer leverkusen",
        "borussia monchengladbach", "eintracht frankfurt", "wolfsburg",
        # Ligue 1
        "psg", "marseille", "lyon", "monaco", "lille",
        # Other top clubs
        "porto", "benfica", "sporting cp", "ajax", "psv",
        "celtic", "rangers", "galatasaray", "fenerbahce",
        "al nassr", "al hilal", "inter miami",
    ]

    # Use normalized query for all subsequent matching
    q = q_normalized

    # Check for player stats intent — only if exactly one known player mentioned
    matched_players = [(name, pid) for name, pid in KNOWN_PLAYER_IDS.items() if name in q]
    if matched_players and len(matched_players) == 1:
        for kw in stats_keywords:
            if kw in q:
                player_name, _ = matched_players[0]
                return {"intent": "player_stats", "player_name": player_name}
        # Also trigger if query is just the player name + simple lookup words
        for kw2 in ["stats of", "stats for", "profile of", "profile for", "info on", "info about", "details of"]:
            if kw2 in q:
                player_name, _ = matched_players[0]
                return {"intent": "player_stats", "player_name": player_name}

    detected_club = None
    for club in known_clubs:
        if club in q:
            detected_club = club.title()
            break

    for kw in graph_keywords:
        if kw in q:
            return {"intent": "graph", "club": detected_club}

    # Multi-club query
    # Detect clubs using fuzzy matching to handle typos like "paris saint german"
    from difflib import SequenceMatcher
    def club_in_query(club: str, query: str) -> bool:
        # Exact substring match first
        if club in query:
            return True
        # Fuzzy match for multi-word clubs (handles typos)
        if len(club) > 6:
            words = query.split()
            for i in range(len(words)):
                for j in range(i+2, min(i+5, len(words)+1)):
                    phrase = " ".join(words[i:j])
                    ratio = SequenceMatcher(None, club, phrase).ratio()
                    if ratio > 0.82:
                        return True
        return False

    clubs_mentioned = [c for c in known_clubs if club_in_query(c, q)]
    if ("played for both" in q or "both" in q or ("and" in q and len(clubs_mentioned) >= 2) or len(clubs_mentioned) >= 2) and len(clubs_mentioned) >= 2:
        return {"intent": "graph_multi", "clubs": clubs_mentioned}  # all clubs, not just 2

    # Transfer history query
    transfer_history_keywords = [
        "transfer history", "career path", "club history",
        "how did", "which clubs has", "moved from"
    ]

    for kw in transfer_history_keywords:
        if kw in q:
            cleaned = q.replace(kw, "").replace("of", "").replace("for", "").replace("?", "").strip()

# normalize known players
            if cleaned in KNOWN_PLAYER_IDS:
                cleaned = KNOWN_PLAYER_IDS[cleaned]

            if cleaned:
                return {"intent": "graph_transfer_history", "player_name": cleaned}

    graph_analysis_keywords = ["most attackers", "most defenders", "most goalkeepers", "most midfielders",
                                "most foreign", "most diverse", "which club has the most", "how many nationalities",
                                "most players from one country", "same country", "one country",
                                "nationalities at", "nationalities in", "most represented", "nationality breakdown",
                                "most number of", "most spanish", "most french", "most english", "most german",
                                "most brazilian", "most argentinian", "most italian", "most portuguese",
                                "most brazilians", "most argentinians", "most italians", "most portuguese",
                                "most spaniards", "most frenchmen", "most englishmen", "most germans"]
    for kw in graph_analysis_keywords:
        if kw in q:
            return {"intent": "graph_analysis", "query": q}

    # Nationality query
    nationality_map = {
        "french": "France", "english": "England", "spanish": "Spain",
        "german": "Germany", "brazilian": "Brazil", "argentinian": "Argentina",
        "portuguese": "Portugal", "italian": "Italy", "dutch": "Netherlands",
        "belgian": "Belgium", "uruguayan": "Uruguay", "moroccan": "Morocco"
    }

    # Detect league mention for filtering (used by graph_nationality)
    _LEAGUE_NAMES = ["premier league", "la liga", "serie a", "bundesliga", "ligue 1"]
    _LEAGUE_ALIASES = {
        "epl": "premier league", "prem": "premier league", "pl": "premier league",
        "english premier league": "premier league", "spanish league": "la liga",
        "primera division": "la liga", "italian league": "serie a", "calcio": "serie a",
        "german league": "bundesliga", "french league": "ligue 1",
    }
    detected_league = None
    for alias, league in _LEAGUE_ALIASES.items():
        if alias in q:
            detected_league = league
            break
    if not detected_league:
        for league in _LEAGUE_NAMES:
            if league in q:
                detected_league = league
                break

    for nat_adj, nat_name in nationality_map.items():
        if nat_adj in q and any(w in q for w in ["players", "who", "list", "show", "find", "all", "how many", "are there",
                                                   "centre-back", "goalkeeper", "midfielder", "attacker", "defender", "striker", "winger"]):
            # Check if position is also mentioned
            position = None
            if "centre-back" in q or "center-back" in q:
                position = "Centre-Back"
            elif "goalkeeper" in q:
                position = "Goalkeeper"
            elif "midfielder" in q:
                position = "Midfield"
            elif "attacker" in q or "striker" in q or "forward" in q:
                position = "Attacker"
            elif "winger" in q:
                position = "Winger"
            return {"intent": "graph_nationality", "nationality": nat_name, "position": position, "league": detected_league, "club": detected_club}

    for kw in api_keywords:
        if kw in q:
            return {"intent": "api", "club": detected_club}

    # Position filter query — "show all attackers in barcelona/laliga"
    position_keywords = {
        "attacker": "Attack", "attackers": "Attack", "striker": "Attack", "strikers": "Attack",
        "forward": "Attack", "forwards": "Attack",
        "defender": "Defender", "defenders": "Defender", "centre-back": "Defender", "center-back": "Defender",
        "midfielder": "Midfield", "midfielders": "Midfield",
        "goalkeeper": "Goalkeeper", "goalkeepers": "Goalkeeper", "keeper": "Goalkeeper",
        "winger": "Winger", "wingers": "Winger",
    }
    detected_position = None
    for kw, pos in position_keywords.items():
        if kw in q:
            detected_position = pos
            break
    if detected_position and (detected_club or detected_league):
        return {"intent": "graph_position", "position": detected_position, "club": detected_club, "league": detected_league}

    if detected_club and any(w in q for w in ["show", "list", "get", "give"]):
        return {"intent": "api", "club": detected_club}

    return {"intent": "llm", "club": None}


def _player_stats_from_llm(player_name: str) -> dict:
    """Fallback when api-football limit is hit — ask LLM to fill the same data structure."""
    prompt = f"""Return a JSON object with stats for {player_name} for the most recent completed season you know about.
Use exactly this structure, fill with your best knowledge:
{{
  "name": "full name",
  "age": number,
  "nationality": "country",
  "position": "position",
  "currentTeam": "club name",
  "seasonLabel": "YYYY/YY",
  "season2024": {{
    "appearances": number or null,
    "goals": number or null,
    "assists": number or null,
    "yellowCards": number or null,
    "redCards": number or null,
    "rating": "number as string" or null
  }},
  "trophiesWon": ["Trophy (Season)", ...],
  "transferHistory": [{{"date": "YYYY-MM-DD", "from": "club", "to": "club", "fee": "amount"}}]
}}
Return ONLY the JSON, no explanation."""

    try:
        import json as _json
        from llm import chat
        raw = chat(prompt, system="You are a football data expert. Return only valid JSON.", max_tokens=600)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = _json.loads(raw[start:end])
        return {"source": "llm_fallback", "data": data}
    except Exception:
        return {"source": "llm_fallback", "data": {"name": player_name, "note": "Stats unavailable — API limit reached and LLM fallback failed."}}


ESPN_LEAGUE_SLUGS_MAP = {
    "premier league": "eng.1",
    "championship": "eng.2",
    "la liga": "esp.1",
    "serie a": "ita.1",
    "bundesliga": "ger.1",
    "ligue 1": "fra.1",
    "eredivisie": "ned.1",
    "primeira liga": "por.1",
    "pro league": "bel.1",
    "super lig": "tur.1",
    "premiership": "sco.1",
    "mls": "usa.1",
    "liga mx": "mex.1",
    "brasileirao": "bra.1",
    "liga profesional": "arg.1",
    "champions league": "uefa.champions",
    "europa league": "uefa.europa",
    "conference league": "uefa.europa.conf",
}
ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"

ESPN_POSITION_MAP = {
    "Attack": ["Forward", "Attacker", "Striker", "Winger", "Centre-Forward", "Second Striker"],
    "Defender": ["Defender", "Centre-Back", "Full-Back", "Left-Back", "Right-Back", "Wing-Back"],
    "Midfield": ["Midfielder", "Midfield", "Defensive Midfield", "Central Midfield", "Attacking Midfield"],
    "Goalkeeper": ["Goalkeeper", "Goalie"],
}

def _fetch_espn_position_counts(league: str, position_key: str) -> list:
    """Fetch first-team squads from ESPN and count players by position per club."""
    slug = ESPN_LEAGUE_SLUGS_MAP.get(league)
    if not slug:
        return []
    try:
        r = requests.get(f"{ESPN_BASE_URL}/{slug}/teams", timeout=8)
        teams = r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    except Exception:
        return []

    pos_keywords = ESPN_POSITION_MAP.get(position_key, [position_key])
    club_counts = []

    for t in teams:
        team_id = t["team"]["id"]
        team_name = t["team"]["displayName"]
        try:
            roster_res = requests.get(f"{ESPN_BASE_URL}/{slug}/teams/{team_id}/roster", timeout=8)
            athletes = roster_res.json().get("athletes", [])
            count = sum(
                1 for p in athletes
                if any(kw.lower() in p.get("position", {}).get("displayName", "").lower() for kw in pos_keywords)
            )
            club_counts.append({"club": team_name, "count": count})
        except Exception:
            continue

    club_counts.sort(key=lambda x: x["count"], reverse=True)
    return club_counts[:5]


import time as _time

_ESPN_TEAMS_CACHE: list = []
_ESPN_TEAMS_CACHE_TS: float = 0
_ESPN_TEAMS_CACHE_TTL = 24 * 60 * 60  # 24 hours

def _get_all_espn_teams() -> list:
    global _ESPN_TEAMS_CACHE, _ESPN_TEAMS_CACHE_TS
    if _ESPN_TEAMS_CACHE and (_time.time() - _ESPN_TEAMS_CACHE_TS) < _ESPN_TEAMS_CACHE_TTL:
        return _ESPN_TEAMS_CACHE

    slugs = [
        "eng.1", "eng.2", "eng.3",
        "esp.1", "esp.2",
        "ita.1", "ita.2",
        "ger.1", "ger.2",
        "fra.1", "fra.2",
        "ned.1", "por.1", "bel.1", "tur.1", "sco.1",
        "usa.1", "mex.1", "bra.1", "arg.1",
        "uefa.champions", "uefa.europa", "uefa.europa.conf",
    ]
    base = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    all_teams = []
    for slug in slugs:
        try:
            r = requests.get(f"{base}/{slug}/teams", timeout=6)
            teams = r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
            for t in teams:
                all_teams.append({"id": t["team"]["id"], "name": t["team"]["displayName"], "slug": slug})
        except Exception:
            continue

    _ESPN_TEAMS_CACHE = all_teams
    _ESPN_TEAMS_CACHE_TS = _time.time()
    return all_teams


@router.post("/agent")
def smart_agent(query: str):
    parsed = analyze_query(query)
    intent = parsed.get("intent")
    club = parsed.get("club")

    if intent == "player_stats":
        player_name = parsed.get("player_name", "")
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        player_data = None
        found_season = None

        # Try current season first, then fall back to previous
        api_limit_hit = False
        for try_season in [2025, 2024]:
            for league_id in SEARCH_LEAGUES:
                res = requests.get(
                    f"https://v3.football.api-sports.io/players?search={requests.utils.quote(player_name)}&season={try_season}&league={league_id}",
                    headers=headers
                )
                if res.status_code == 200:
                    rj = res.json()
                    errors = rj.get("errors")
                    # Only treat as rate limit if it's actually a plan/request limit error
                    if errors and isinstance(errors, dict) and "requests" in str(errors).lower():
                        api_limit_hit = True
                        break
                    if rj.get("response"):
                        candidate = rj["response"][0]
                        stats = candidate.get("statistics", [{}])[0]
                        if stats.get("games", {}).get("appearences"):
                            player_data = candidate
                            found_season = try_season
                            break
            if api_limit_hit or player_data:
                break

        if api_limit_hit:
            return _player_stats_from_llm(player_name)
        
        # If still nothing, just take first result from 2024 regardless
        if not player_data:
            for league_id in SEARCH_LEAGUES:
                res = requests.get(
                    f"https://v3.football.api-sports.io/players?search={requests.utils.quote(player_name)}&season=2024&league={league_id}",
                    headers=headers
                )
                if res.status_code == 200 and res.json().get("response"):
                    player_data = res.json()["response"][0]
                    found_season = 2024
                    break

        if not player_data:
            # API limit hit or player not found — fallback to LLM
            return _player_stats_from_llm(player_name)

        player = player_data["player"]
        player_id = player["id"]
        stats = player_data.get("statistics", [{}])[0]

        # Fetch trophies
        trophies_res = requests.get(
            f"https://v3.football.api-sports.io/trophies?player={player_id}",
            headers=headers
        )
        trophies = []
        if trophies_res.status_code == 200:
            for t in trophies_res.json().get("response", []):
                if t.get("place") in ("Winner", "1st Place") and t.get("season"):
                    trophies.append(f"{t['league']} ({t['season']})")

        # Fetch transfer history
        transfers_res = requests.get(
            f"https://v3.football.api-sports.io/transfers?player={player_id}",
            headers=headers
        )
        transfer_history = []
        if transfers_res.status_code == 200:
            raw = transfers_res.json().get("response", [])
            if raw:
                for t in raw[0].get("transfers", []):
                    transfer_history.append({
                        "date": t.get("date"),
                        "from": t["teams"]["out"]["name"],
                        "to": t["teams"]["in"]["name"],
                        "fee": t.get("type")
                    })

        season_label = f"{found_season}/{str(found_season+1)[-2:]}" if found_season else "2024/25"

        return {
            "source": "api",
            "data": {
                "name": player.get("name"),
                "age": player.get("age"),
                "nationality": player.get("nationality"),
                "position": stats.get("games", {}).get("position"),
                "currentTeam": stats.get("team", {}).get("name"),
                "seasonLabel": season_label,
                "season2024": {
                    "appearances": stats.get("games", {}).get("appearences"),
                    "goals": stats.get("goals", {}).get("total"),
                    "assists": stats.get("goals", {}).get("assists"),
                    "yellowCards": stats.get("cards", {}).get("yellow"),
                    "redCards": stats.get("cards", {}).get("red"),
                    "rating": stats.get("games", {}).get("rating"),
                },
                "trophiesWon": trophies,
                "transferHistory": transfer_history
            }
        }
    if intent == "graph_transfer_history":
        player_name = parsed.get("player_name", "")
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Player)-[:TRANSFERRED]->(t:Transfer)
                WHERE toLower(p.name) CONTAINS toLower($name)
                OPTIONAL MATCH (t)-[:FROM]->(c1:Club)
                OPTIONAL MATCH (t)-[:TO]->(c2:Club)
                RETURN p.name AS player,
                       c1.name AS from_club,
                       c2.name AS to_club,
                       t.season AS season,
                       t.fee AS fee
                ORDER BY t.season
            """, {"name": player_name})

            rows = [r for r in result if r["from_club"] or r["to_club"]]
            # Deduplicate — keep unique from->to pairs
            seen = set()
            data = []
            for r in rows:
                key = (r["from_club"], r["to_club"])
                if key not in seen:
                    seen.add(key)
                    data.append({
                        "from_club": r["from_club"],
                        "to_club": r["to_club"],
                        "season": r["season"],
                        "fee": r["fee"]
                    })

        if not data:
            # Fallback to PLAYED_FOR clubs list
            with driver.session() as session:
                result = session.run("""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE toLower(p.name) CONTAINS toLower($name)
                    RETURN DISTINCT c.name AS club
                """, {"name": player_name})
                clubs = [r["club"] for r in result if r["club"]]
            if clubs:
                return {"source": "graph", "data": {"player": player_name, "clubs": clubs}}
            return {"source": "graph", "data": f"No transfer history found for {player_name}"}

        return {"source": "graph", "data": {"player": player_name, "transfers": data}}

    if intent == "graph_analysis":
        q_lower = parsed.get("query", "").lower()
        nationality_map = {
            "french": "France", "english": "England", "spanish": "Spain",
            "german": "Germany", "brazilian": "Brazil", "argentinian": "Argentina",
            "portuguese": "Portugal", "italian": "Italy", "dutch": "Netherlands",
            "belgian": "Belgium", "uruguayan": "Uruguay", "moroccan": "Morocco",
            "brazilians": "Brazil", "argentinians": "Argentina", "italians": "Italy",
            "spaniards": "Spain", "frenchmen": "France", "englishmen": "England", "germans": "Germany"
        }

        # League filter detection — use keyword lists for CONTAINS matching
        LEAGUE_KEYWORDS = {
            "premier league": ["Arsenal", "Chelsea", "Liverpool", "Manchester City", "Manchester United",
                               "Tottenham", "Newcastle", "Aston Villa", "West Ham", "Brighton",
                               "Everton", "Fulham", "Brentford", "Crystal Palace", "Wolverhampton",
                               "Nottingham Forest", "Bournemouth", "Burnley", "Luton", "Sheffield United",
                               "Leicester", "Leeds", "Southampton"],
            "la liga": ["Barcelona", "Real Madrid", "Atletico", "Sevilla", "Valencia",
                        "Villarreal", "Real Sociedad", "Athletic", "Real Betis"],
            "serie a": ["Juventus", "Milan", "Inter", "Napoli", "Roma", "Lazio",
                        "Atalanta", "Fiorentina", "Torino"],
            "bundesliga": ["Bayern", "Dortmund", "Leipzig", "Leverkusen",
                           "Mönchengladbach", "Frankfurt", "Wolfsburg"],
            "ligue 1": ["Paris Saint-Germain", "Marseille", "Lyon", "Monaco", "Lille"],
        }
        LEAGUE_ALIASES = {
            "epl": "premier league", "english premier league": "premier league",
            "prem": "premier league", "pl": "premier league",
            "spanish league": "la liga", "primera division": "la liga",
            "italian league": "serie a", "calcio": "serie a",
            "german league": "bundesliga",
            "french league": "ligue 1",
        }

        detected_league = None
        for alias, league in LEAGUE_ALIASES.items():
            if alias in q_lower:
                detected_league = league
                break
        if not detected_league:
            for league in LEAGUE_KEYWORDS:
                if league in q_lower:
                    detected_league = league
                    break

        league_keywords = LEAGUE_KEYWORDS.get(detected_league, []) if detected_league else []

        # Build league filter as a series of OR CONTAINS conditions
        def build_league_filter(keywords, club_var="c"):
            if not keywords:
                return "", {}
            conditions = " OR ".join([f"{club_var}.name CONTAINS $lk{i}" for i, _ in enumerate(keywords)])
            params = {f"lk{i}": kw for i, kw in enumerate(keywords)}
            return f"AND ({conditions})", params

        with driver.session() as session:
            detected_nat = None
            for adj, country in nationality_map.items():
                if adj in q_lower:
                    detected_nat = country
                    break

            league_filter, params_base = build_league_filter(league_keywords)

            if detected_nat:
                if league_keywords:
                    lf = "AND any(kw IN $lkws WHERE p.current_club_name CONTAINS kw)"
                    nat_params = {"nat": detected_nat, "lkws": league_keywords}
                else:
                    lf = ""
                    nat_params = {"nat": detected_nat}
                result = session.run(f"""
                    MATCH (p:Player)
                    WHERE p.nationality = $nat AND p.current_club_name IS NOT NULL AND p.current_club_name <> 'None'
                    {lf}
                    RETURN p.current_club_name AS club, count(DISTINCT p) AS count
                    ORDER BY count DESC LIMIT 5
                """, nat_params)
            elif "attacker" in q_lower or "forward" in q_lower or "striker" in q_lower:
                if detected_league:
                    data = _fetch_espn_position_counts(detected_league, "Attack")
                    return {"source": "graph", "data": data}
                result = session.run(f"""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE p.position = 'Attack' AND c.name IS NOT NULL AND c.name <> 'None'
                    {league_filter}
                    RETURN c.name AS club, count(p) AS count
                    ORDER BY count DESC LIMIT 5
                """, params_base)
            elif "defender" in q_lower or "defence" in q_lower:
                if detected_league:
                    data = _fetch_espn_position_counts(detected_league, "Defender")
                    return {"source": "graph", "data": data}
                result = session.run(f"""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE p.position = 'Defender' AND c.name IS NOT NULL AND c.name <> 'None'
                    {league_filter}
                    RETURN c.name AS club, count(p) AS count
                    ORDER BY count DESC LIMIT 5
                """, params_base)
            elif "goalkeeper" in q_lower:
                if detected_league:
                    data = _fetch_espn_position_counts(detected_league, "Goalkeeper")
                    return {"source": "graph", "data": data}
                result = session.run(f"""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE p.position = 'Goalkeeper' AND c.name IS NOT NULL AND c.name <> 'None'
                    {league_filter}
                    RETURN c.name AS club, count(p) AS count
                    ORDER BY count DESC LIMIT 5
                """, params_base)
            elif "midfielder" in q_lower:
                if detected_league:
                    data = _fetch_espn_position_counts(detected_league, "Midfield")
                    return {"source": "graph", "data": data}
                result = session.run(f"""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE p.position = 'Midfield' AND c.name IS NOT NULL AND c.name <> 'None'
                    {league_filter}
                    RETURN c.name AS club, count(p) AS count
                    ORDER BY count DESC LIMIT 5
                """, params_base)
            elif "foreign" in q_lower or "diverse" in q_lower or "nationalities" in q_lower or "most represented" in q_lower or "nationality breakdown" in q_lower:
                club_filter = None
                for club in known_clubs_local:
                    if club in q_lower:
                        club_filter = club
                        break
                if club_filter:
                    result = session.run("""
                        MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                        WHERE toLower(c.name) CONTAINS toLower($club)
                        RETURN p.nationality AS club, count(p) AS count
                        ORDER BY count DESC LIMIT 10
                    """, {"club": club_filter})
                else:
                    result = session.run(f"""
                        MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                        WHERE c.name IS NOT NULL AND c.name <> 'None'
                        {league_filter}
                        RETURN c.name AS club, count(DISTINCT p.nationality) AS count
                        ORDER BY count DESC LIMIT 5
                    """, params_base)
            elif "one country" in q_lower or "same country" in q_lower or "most players from" in q_lower:
                result = session.run(f"""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE c.name IS NOT NULL AND c.name <> 'None' AND p.nationality IS NOT NULL
                    {league_filter}
                    WITH c.name AS club, p.nationality AS nationality, count(p) AS cnt
                    ORDER BY cnt DESC
                    WITH club, collect({{nationality: nationality, cnt: cnt}})[0] AS top
                    RETURN club, top.nationality + ' (' + toString(top.cnt) + ')' AS count
                    ORDER BY top.cnt DESC LIMIT 5
                """, params_base)
            else:
                result = session.run(f"""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE c.name IS NOT NULL AND c.name <> 'None'
                    {league_filter}
                    RETURN c.name AS club, count(p) AS count
                    ORDER BY count DESC LIMIT 5
                """, params_base)
            data = [{"club": r["club"], "count": r["count"]} for r in result]
        return {"source": "graph", "data": data}

    if intent == "graph_multi":
        clubs = parsed.get("clubs", [])
        if len(clubs) < 2:
            return {"source": "graph", "data": "Please mention two or more clubs."}
        with driver.session() as session:
            # Build dynamic query for any number of clubs
            match_clauses = []
            params = {}
            for i, club in enumerate(clubs):
                match_clauses.append(f"""
                MATCH (p)-[:PLAYED_FOR]->(c{i}:Club)
                WHERE toLower(c{i}.name) CONTAINS toLower($club{i})""")
                params[f"club{i}"] = club

            query = "MATCH (p:Player)" + "".join(match_clauses) + "\nRETURN DISTINCT p.name AS player ORDER BY p.name"
            result = session.run(query, params)
            players = [r["player"] for r in result if r["player"]]

        club_names = " and ".join(c.title() for c in clubs)
        if not players:
            return {"source": "graph", "data": f"No players found who played for all of: {club_names}"}
        return {"source": "graph", "data": players}

    if intent == "graph_nationality":
        nationality = parsed.get("nationality", "")
        position = parsed.get("position")
        league = parsed.get("league")
        specific_club = parsed.get("club")

        LEAGUE_KEYWORDS = {
            "premier league": ["Arsenal", "Chelsea", "Liverpool", "Manchester City", "Manchester United",
                               "Tottenham", "Newcastle", "Aston Villa", "West Ham", "Brighton",
                               "Everton", "Fulham", "Brentford", "Crystal Palace", "Wolverhampton",
                               "Nottingham Forest", "Bournemouth", "Burnley", "Luton", "Sheffield United",
                               "Leicester", "Leeds", "Southampton"],
            "la liga": ["Barcelona", "Real Madrid", "Atletico", "Sevilla", "Valencia",
                        "Villarreal", "Real Sociedad", "Athletic", "Real Betis"],
            "serie a": ["Juventus", "Milan", "Inter", "Napoli", "Roma", "Lazio",
                        "Atalanta", "Fiorentina", "Torino"],
            "bundesliga": ["Bayern", "Dortmund", "Leipzig", "Leverkusen",
                           "Mönchengladbach", "Frankfurt", "Wolfsburg"],
            "ligue 1": ["Paris Saint-Germain", "Marseille", "Lyon", "Monaco", "Lille"],
        }

        league_kws = LEAGUE_KEYWORDS.get(league, []) if league else []

        with driver.session() as session:
            # Specific club filter takes priority over league filter
            if specific_club:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.nationality = $nat
                    AND p.current_club_name IS NOT NULL
                    AND toLower(p.current_club_name) CONTAINS toLower($club)
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position
                    ORDER BY p.name
                """, {"nat": nationality, "club": specific_club})
            elif position and league_kws:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.nationality = $nat AND p.position CONTAINS $pos
                    AND p.current_club_name IS NOT NULL
                    AND any(kw IN $keywords WHERE p.current_club_name CONTAINS kw)
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position
                    ORDER BY club
                """, {"nat": nationality, "pos": position, "keywords": league_kws})
            elif position:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.nationality = $nat AND p.position CONTAINS $pos
                    AND p.current_club_name IS NOT NULL
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position
                    ORDER BY club
                """, {"nat": nationality, "pos": position})
            else:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.nationality = $nat
                    AND p.current_club_name IS NOT NULL
                    AND any(kw IN $keywords WHERE p.current_club_name CONTAINS kw)
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position
                    ORDER BY club
                """, {"nat": nationality, "keywords": league_kws if league_kws else [""]})
            data = [{"player": r["player"], "club": r["club"], "position": r["position"]} for r in result]
        if not data:
            return {"source": "graph", "data": f"No {nationality} players found. Try syncing squads first."}
        return {"source": "graph", "data": data}

    if intent == "graph_position":
        position = parsed.get("position", "")
        specific_club = parsed.get("club")
        league = parsed.get("league")

        LEAGUE_KEYWORDS = {
            "premier league": ["Arsenal", "Chelsea", "Liverpool", "Manchester City", "Manchester United",
                               "Tottenham", "Newcastle", "Aston Villa", "West Ham", "Brighton",
                               "Everton", "Fulham", "Brentford", "Crystal Palace", "Wolverhampton",
                               "Nottingham Forest", "Bournemouth", "Burnley", "Luton", "Sheffield United",
                               "Leicester", "Leeds", "Southampton"],
            "la liga": ["Barcelona", "Real Madrid", "Atletico", "Sevilla", "Valencia",
                        "Villarreal", "Real Sociedad", "Athletic", "Real Betis"],
            "serie a": ["Juventus", "Milan", "Inter", "Napoli", "Roma", "Lazio",
                        "Atalanta", "Fiorentina", "Torino"],
            "bundesliga": ["Bayern", "Dortmund", "Leipzig", "Leverkusen",
                           "Mönchengladbach", "Frankfurt", "Wolfsburg"],
            "ligue 1": ["Paris Saint-Germain", "Marseille", "Lyon", "Monaco", "Lille"],
        }
        league_kws = LEAGUE_KEYWORDS.get(league, []) if league else []

        with driver.session() as session:
            if specific_club:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.position CONTAINS $pos
                    AND p.current_club_name IS NOT NULL
                    AND toLower(p.current_club_name) CONTAINS toLower($club)
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position, p.nationality AS nationality
                    ORDER BY p.name
                """, {"pos": position, "club": specific_club})
            elif league_kws:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.position CONTAINS $pos
                    AND p.current_club_name IS NOT NULL
                    AND any(kw IN $keywords WHERE p.current_club_name CONTAINS kw)
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position, p.nationality AS nationality
                    ORDER BY club, p.name
                """, {"pos": position, "keywords": league_kws})
            else:
                result = session.run("""
                    MATCH (p:Player)
                    WHERE p.position CONTAINS $pos AND p.current_club_name IS NOT NULL
                    RETURN p.name AS player, p.current_club_name AS club, p.position AS position, p.nationality AS nationality
                    ORDER BY club, p.name
                    LIMIT 100
                """, {"pos": position})
            data = [{"player": r["player"], "club": r["club"], "position": r["position"]} for r in result]
        if not data:
            return {"source": "graph", "data": f"No {position} players found in our database."}
        return {"source": "graph", "data": data}

    if intent == "graph":
        with driver.session() as session:
            if club:
                result = session.run("""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    WHERE toLower(c.name) CONTAINS toLower($club)
                    RETURN p.name AS player, c.name AS club
                    LIMIT 10
                """, {"club": club})
            else:
                result = session.run("""
                    MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                    RETURN p.name AS player, c.name AS club
                """)
            data = [{"player": r["player"], "club": r["club"]} for r in result]

        context = " ".join([f"{item['player']} plays for {item['club']}." for item in data])

        try:
            response_text = chat(
                f"Data: {context}\n\nQuestion: {query}\n\nAnswer using only the data above.",
                system="You are a football assistant. Use ONLY the provided data. Do NOT make assumptions. Keep it 1-2 sentences."
            )
            return {"source": "graph_db + llm", "data": response_text}
        except Exception:
            return {"source": "graph_db", "data": data}

    elif intent == "api" and club:
        ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
        club_search = club.lower().strip()

        # Collect all teams — from cache after first call
        all_teams = _get_all_espn_teams()

        # Common name aliases for ESPN lookup (user term -> ESPN display name substring)
        COMMON_NAME_MAP = {
            "inter milan": "internazionale",
            "inter": "internazionale",
            "psg": "paris saint-germain",
            "paris saint germain": "paris saint-germain",
            "atletico madrid": "atlético de madrid",
            "atletico": "atlético",
            "real betis": "betis",
            "sporting cp": "sporting",
            "al nassr": "al-nassr",
            "al hilal": "al-hilal",
        }
        search_term = COMMON_NAME_MAP.get(club_search, club_search)

        # Score matches — prefer full name match over partial
        def match_score(team_name: str, search: str) -> int:
            n = team_name.lower()
            if n == search:
                return 100
            if search in n and len(search) > 4:
                return 60
            if n in search:
                return 40
            return 0

        best = max(all_teams, key=lambda t: match_score(t["name"], search_term), default=None)
        if not best or match_score(best["name"], search_term) == 0:
            return {"source": "api", "data": f"Team '{club}' not found"}

        espn_team_id = best["id"]
        espn_slug = best["slug"]

        roster_res = requests.get(f"{ESPN_BASE}/{espn_slug}/teams/{espn_team_id}/roster")
        if roster_res.status_code != 200:
            return {"source": "api", "data": "Could not fetch squad"}

        athletes = roster_res.json().get("athletes", [])
        squad = [
            {"name": p.get("displayName"), "position": p.get("position", {}).get("displayName", "Unknown")}
            for p in athletes
        ]
        return {"source": "api", "data": squad}

    else:
        try:
            response_text = chat(query, max_tokens=3000)
            return {"source": "llm", "data": response_text}
        except Exception:
            return {"source": "llm", "data": "AI unavailable — make sure Groq API key is set."}

