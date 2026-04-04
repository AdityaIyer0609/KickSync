import requests
from fastapi import APIRouter
from config import API_KEY, driver
from utils import get_team_id

router = APIRouter()


@router.get("/player/{player_id}")
def get_player(player_id: int):
    headers = {"X-Auth-Token": API_KEY}

    profile_res = requests.get(f"https://api.football-data.org/v4/persons/{player_id}", headers=headers)
    if profile_res.status_code != 200:
        return {"error": "Player not found"}
    profile = profile_res.json()

    matches_res = requests.get(
        f"https://api.football-data.org/v4/persons/{player_id}/matches?limit=10",
        headers=headers
    )
    aggregations = {}
    if matches_res.status_code == 200:
        aggregations = matches_res.json().get("aggregations", {})

    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "position": profile.get("position"),
        "nationality": profile.get("nationality"),
        "dateOfBirth": profile.get("dateOfBirth"),
        "shirtNumber": profile.get("shirtNumber"),
        "currentTeam": profile.get("currentTeam", {}).get("name"),
        "stats": aggregations
    }


@router.get("/players")
def get_players():
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
            RETURN p.name AS player, c.name AS club, p.position AS position, p.nationality AS nationality
        """)
        return [{"player": r["player"], "club": r["club"], "position": r["position"], "nationality": r["nationality"]} for r in result]


@router.get("/graph-stats")
def graph_stats():
    """Return counts of nodes in the graph."""
    with driver.session() as session:
        players = session.run("MATCH (p:Player) RETURN count(p) AS count").single()["count"]
        clubs = session.run("MATCH (c:Club) RETURN count(c) AS count").single()["count"]
        nations = session.run("MATCH (n:Nation) RETURN count(n) AS count").single()["count"]
        return {"players": players, "clubs": clubs, "nations": nations}


@router.post("/sync-squad/{team_name}")
def sync_squad(team_name: str):
    """Fetch squad from football-data.org and write into Neo4j."""
    team_id = get_team_id(team_name)
    if not team_id:
        return {"error": f"Team '{team_name}' not found"}

    headers = {"X-Auth-Token": API_KEY}
    res = requests.get(f"https://api.football-data.org/v4/teams/{team_id}", headers=headers)
    if res.status_code != 200:
        return {"error": "Could not fetch team data"}

    data = res.json()
    club_name = data.get("name")
    squad = data.get("squad", [])

    if not squad:
        return {"error": f"No squad data available for {club_name}"}

    synced = []
    with driver.session() as session:
        # Create the club node
        session.run("MERGE (c:Club {name: $name})", {"name": club_name})

        for player in squad:
            name = player.get("name")
            position = player.get("position", "Unknown")
            nationality = player.get("nationality", "Unknown")
            dob = player.get("dateOfBirth", "")

            if not name:
                continue

            # Create player node with properties
            session.run("""
                MERGE (p:Player {name: $name})
                SET p.position = $position,
                    p.nationality = $nationality,
                    p.dateOfBirth = $dob
            """, {"name": name, "position": position, "nationality": nationality, "dob": dob})

            # Create PLAYS_FOR relationship
            session.run("""
                MATCH (p:Player {name: $player}), (c:Club {name: $club})
                MERGE (p)-[:PLAYED_FOR]->(c)
            """, {"player": name, "club": club_name})

            # Create nationality node and relationship
            if nationality and nationality != "Unknown":
                session.run("""
                    MERGE (n:Nation {name: $nation})
                    WITH n
                    MATCH (p:Player {name: $player})
                    MERGE (p)-[:NATIONALITY]->(n)
                """, {"nation": nationality, "player": name})

            synced.append({"name": name, "position": position, "nationality": nationality})

    return {
        "club": club_name,
        "synced": len(synced),
        "players": synced
    }


@router.post("/sync-all-squads")
def sync_all_squads():
    """Sync squads for all major clubs into Neo4j in one call."""
    from utils import get_team_id

    clubs = [
        "Arsenal", "Chelsea", "Liverpool", "Manchester City", "Manchester United",
        "Tottenham", "Newcastle", "Aston Villa", "Barcelona", "Real Madrid",
        "Atletico Madrid", "Bayern Munich", "Borussia Dortmund", "PSG",
        "Juventus", "AC Milan", "Inter Milan", "Napoli"
    ]

    results = []
    for club in clubs:
        try:
            result = sync_squad(club)
            results.append({"club": club, "synced": result.get("synced", 0), "status": "ok"})
        except Exception as e:
            results.append({"club": club, "synced": 0, "status": str(e)})

    total = sum(r["synced"] for r in results)
    return {"total_players_synced": total, "clubs": results}



def graph_query(q: str):
    """
    Run common graph queries.
    Examples:
      ?q=nationality:French
      ?q=position:Goalkeeper
      ?q=club:Arsenal
      ?q=multi-club:Arsenal,Chelsea
    """
    with driver.session() as session:
        if q.startswith("nationality:"):
            nation = q.split(":", 1)[1]
            result = session.run("""
                MATCH (p:Player)-[:NATIONALITY]->(n:Nation {name: $nation})
                OPTIONAL MATCH (p)-[:PLAYED_FOR]->(c:Club)
                RETURN p.name AS player, c.name AS club, p.position AS position
            """, {"nation": nation})
            return [{"player": r["player"], "club": r["club"], "position": r["position"]} for r in result]

        elif q.startswith("position:"):
            pos = q.split(":", 1)[1]
            result = session.run("""
                MATCH (p:Player {position: $pos})-[:PLAYED_FOR]->(c:Club)
                RETURN p.name AS player, c.name AS club, p.nationality AS nationality
            """, {"pos": pos})
            return [{"player": r["player"], "club": r["club"], "nationality": r["nationality"]} for r in result]

        elif q.startswith("multi-club:"):
            clubs = q.split(":", 1)[1].split(",")
            if len(clubs) < 2:
                return {"error": "Provide two clubs separated by comma"}
            result = session.run("""
                MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club)
                WHERE toLower(c1.name) CONTAINS toLower($club1)
                MATCH (p)-[:PLAYED_FOR]->(c2:Club)
                WHERE toLower(c2.name) CONTAINS toLower($club2)
                RETURN p.name AS player
            """, {"club1": clubs[0].strip(), "club2": clubs[1].strip()})
            return [{"player": r["player"]} for r in result]

        elif q.startswith("club:"):
            club = q.split(":", 1)[1]
            result = session.run("""
                MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                WHERE toLower(c.name) CONTAINS toLower($club)
                RETURN p.name AS player, p.position AS position, p.nationality AS nationality
                ORDER BY p.position
            """, {"club": club})
            return [{"player": r["player"], "position": r["position"], "nationality": r["nationality"]} for r in result]

        return {"error": "Unknown query format"}


@router.post("/sync-transfers")
def sync_transfers():
    """
    For every player in Neo4j, fetch their transfer history from api-football
    and write PREVIOUSLY_PLAYED_FOR relationships.
    """
    from config import API_FOOTBALL_KEY
    af_headers = {"x-apisports-key": API_FOOTBALL_KEY}

    # Get all players from Neo4j
    with driver.session() as session:
        result = session.run("MATCH (p:Player) RETURN p.name AS name")
        players = [r["name"] for r in result]

    print(f"Syncing transfers for {len(players)} players...")
    synced = 0
    errors = 0

    for player_name in players:
        try:
            # Search api-football for player ID
            res = requests.get(
                f"https://v3.football.api-sports.io/players?search={requests.utils.quote(player_name)}&season=2024&league=39",
                headers=af_headers
            )
            if res.status_code != 200 or res.json().get("errors"):
                continue
            response = res.json().get("response", [])
            if not response:
                # Try other leagues
                for league_id in [140, 135, 78, 61]:
                    res2 = requests.get(
                        f"https://v3.football.api-sports.io/players?search={requests.utils.quote(player_name)}&season=2024&league={league_id}",
                        headers=af_headers
                    )
                    if res2.status_code == 200 and not res2.json().get("errors") and res2.json().get("response"):
                        response = res2.json()["response"]
                        break

            if not response:
                continue

            player_id = response[0]["player"]["id"]

            # Fetch transfer history
            tr = requests.get(
                f"https://v3.football.api-sports.io/transfers?player={player_id}",
                headers=af_headers
            )
            if tr.status_code != 200 or tr.json().get("errors"):
                continue

            transfers = tr.json().get("response", [])
            if not transfers:
                continue

            with driver.session() as session:
                for t in transfers[0].get("transfers", []):
                    club_name = t["teams"]["in"]["name"]
                    transfer_date = t.get("date", "")
                    fee = t.get("type", "")

                    # Create club node if not exists
                    session.run("MERGE (c:Club {name: $name})", {"name": club_name})

                    # Create PREVIOUSLY_PLAYED_FOR relationship
                    session.run("""
                        MATCH (p:Player {name: $player}), (c:Club {name: $club})
                        MERGE (p)-[r:PREVIOUSLY_PLAYED_FOR]->(c)
                        SET r.date = $date, r.fee = $fee
                    """, {"player": player_name, "club": club_name, "date": transfer_date, "fee": fee})

            synced += 1

        except Exception as e:
            errors += 1
            continue

    return {"synced": synced, "errors": errors, "total_players": len(players)}


def test_db():
    with driver.session() as session:
        result = session.run("RETURN 'Neo4j connected 🚀' AS message")
        return [record["message"] for record in result]
