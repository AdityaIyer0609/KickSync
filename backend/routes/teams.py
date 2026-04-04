import requests
from fastapi import APIRouter
from config import API_KEY
from utils import get_team_id
from llm import chat

router = APIRouter()


@router.get("/teams")
def get_teams():
    url = "https://api.football-data.org/v4/competitions/PL/teams"
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()
    return [
        {"name": t["name"], "shortName": t["shortName"], "crest": t["crest"]}
        for t in data.get("teams", [])
    ]


@router.get("/tactics/{team_name}")
def get_tactics(team_name: str):
    team_id = get_team_id(team_name)
    if not team_id:
        return {"error": "Team not found"}

    headers = {"X-Auth-Token": API_KEY}
    res = requests.get(f"https://api.football-data.org/v4/teams/{team_id}", headers=headers)
    if res.status_code != 200:
        return {"error": "Could not fetch team data"}

    data = res.json()
    squad = data.get("squad", [])

    positions = {}
    for p in squad:
        pos = p.get("position", "Unknown")
        positions.setdefault(pos, []).append(p["name"])

    position_summary = "\n".join([f"{pos}: {', '.join(names)}" for pos, names in positions.items()])

    prompt = f"""
You are a football tactics expert. Analyze this squad and suggest:
1. Best formation
2. Key strengths
3. Potential weaknesses
4. Tactical style recommendation

Squad breakdown:
{position_summary}

Keep it concise, 4-5 sentences max.
"""

    try:
        tactical_analysis = chat(prompt, system="You are a football tactics expert. Be concise and accurate.")
    except Exception:
        tactical_analysis = "AI analysis unavailable."

    return {
        "team": data.get("name"),
        "squad_size": len(squad),
        "positions": positions,
        "tactical_analysis": tactical_analysis
    }
