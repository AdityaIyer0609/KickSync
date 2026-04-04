import requests
import unicodedata
from config import API_KEY, KNOWN_TEAM_IDS


def normalize(text: str) -> str:
    """Remove accents and lowercase for fuzzy matching."""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower().strip()


def get_team_id(team_name: str):
    key = normalize(team_name)

    # Require minimum 4 chars to avoid single-digit false matches
    for known, tid in KNOWN_TEAM_IDS.items():
        known_norm = normalize(known)
        if len(known_norm) >= 4 and len(key) >= 4:
            if known_norm in key or key in known_norm:
                return tid

    # Fallback to API search
    url = f"https://api.football-data.org/v4/teams?name={requests.utils.quote(team_name)}"
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()
    teams = data.get("teams", [])
    if teams:
        return teams[0]["id"]
    return None
