import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

KNOWN_TEAM_IDS = {
    "barcelona": 81,
    "real madrid": 86,
    "atletico madrid": 78,
    "sevilla": 559,
    "valencia": 95,
    "athletic bilbao": 77,
    "villarreal": 94,
    "real sociedad": 92,
    "manchester united": 66,
    "manchester city": 65,
    "arsenal": 57,
    "chelsea": 61,
    "liverpool": 64,
    "tottenham": 73,
    "newcastle": 67,
    "aston villa": 58,
    "west ham": 563,
    "brighton": 397,
    "everton": 62,
    "fulham": 63,
    "brentford": 402,
    "crystal palace": 354,
    "wolves": 76,
    "nottingham forest": 351,
    "bournemouth": 1044,
    "bayern munich": 5,
    "borussia dortmund": 4,
    "rb leipzig": 721,
    "bayer leverkusen": 3,
    "juventus": 109,
    "ac milan": 98,
    "inter milan": 108,
    "as roma": 100,
    "napoli": 113,
    "lazio": 110,
    "psg": 524,
    "marseille": 516,
    "lyon": 523,
    "ajax": 678,
    "porto": 503,
    "benfica": 498,
    "sporting cp": 498,
}
