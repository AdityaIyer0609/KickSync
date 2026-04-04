import json
import requests
from fastapi import APIRouter
from config import API_KEY
from utils import get_team_id
from llm import chat

router = APIRouter()


@router.get("/transfers/{team_name}")
def get_transfer_suggestions(team_name: str, position: str = None):
    team_id = get_team_id(team_name)
    if not team_id:
        return {"error": "Team not found"}

    headers = {"X-Auth-Token": API_KEY}
    res = requests.get(f"https://api.football-data.org/v4/teams/{team_id}", headers=headers)
    if res.status_code != 200:
        return {"error": "Could not fetch team data"}

    data = res.json()
    squad = data.get("squad", [])

    pos_count = {}
    for p in squad:
        pos = p.get("position", "Unknown")
        pos_count[pos] = pos_count.get(pos, 0) + 1

    if position:
        target_position = position
    else:
        filtered = {k: v for k, v in pos_count.items() if k != "Unknown"}
        target_position = min(filtered, key=filtered.get) if filtered else "Attacker"

    scorers_res = requests.get(
        "https://api.football-data.org/v4/competitions/PL/scorers?limit=20",
        headers=headers
    )

    candidates = []
    if scorers_res.status_code == 200:
        scorers = scorers_res.json().get("scorers", [])
        current_squad_names = {p["name"] for p in squad}
        for s in scorers:
            player = s["player"]
            team = s.get("team", {}).get("name", "Unknown")
            if player["name"] not in current_squad_names:
                candidates.append({
                    "name": player["name"],
                    "position": player.get("position", "Unknown"),
                    "nationality": player.get("nationality"),
                    "currentTeam": team,
                    "goals": s.get("goals"),
                    "assists": s.get("assists")
                })

    prompt = f"""
You are a football transfer analyst. {data.get('name')} needs reinforcement at {target_position}.

Their current squad has: {pos_count}

Available candidates from top scorers:
{json.dumps(candidates[:5], indent=2)}

Suggest 2-3 realistic transfer targets and briefly explain why each fits. Keep it under 5 sentences.
"""

    try:
        suggestion = chat(prompt, system="You are a football transfer analyst. Be concise and realistic.")
    except Exception:
        suggestion = "AI analysis unavailable."

    return {
        "team": data.get("name"),
        "target_position": target_position,
        "squad_positions": pos_count,
        "candidates": candidates[:5],
        "suggestion": suggestion
    }
