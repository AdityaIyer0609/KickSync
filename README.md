# KickSync

An AI-powered football intelligence platform combining real-time match data, graph database relationships, and large language models to deliver live scores, match analysis, squad insights, and tactical intelligence.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, Tailwind CSS, React Markdown |
| Backend | FastAPI (Python) |
| Graph Database | Neo4j AuraDB |
| LLM | Groq API (openai/gpt-oss-120b → llama-3.3-70b fallback) |
| Football Data | football-data.org, api-football.com, ESPN unofficial API |

---

## Project Structure

```
kicksync/
├── backend/
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── config.py            # Env vars, Neo4j driver, known team IDs
│   ├── llm.py               # Groq API wrapper with model fallback
│   ├── utils.py             # Team ID lookup helper
│   ├── load_to_neo4j.py     # One-time CSV → Neo4j data loader
│   ├── routes/
│   │   ├── agent.py         # AI agent — intent routing + query handling
│   │   ├── dashboard.py     # Dashboard endpoints (news, live scores, stats)
│   │   ├── matches.py       # Match list + match detail analysis
│   │   ├── players.py       # Player stats, Neo4j sync
│   │   ├── teams.py         # Squad lookup, league teams
│   │   ├── transfers.py     # Transfer suggestions
│   │   └── chat.py          # Basic chat endpoint
│   ├── data/                # CSV datasets (players, clubs, appearances etc.)
│   └── .env                 # API keys (not committed)
└── frontend/
    └── app/
        ├── page.tsx              # Dashboard — news, recent matches, AI insights, player spotlight
        ├── live/page.tsx         # Live scores — real-time match cards with stats + goal scorers
        ├── chat/page.tsx         # Football Assistant — natural language queries
        ├── matches/page.tsx      # Match browser — league → team → match
        ├── match/[id]/page.tsx   # Match detail — stats, lineups, goals, cards, AI analysis
        └── components/
            ├── Navbar.tsx        # Responsive navbar with hamburger menu
            └── Skeleton.tsx      # Loading skeleton components
```

---

## Pages

### Dashboard (`/`)
- Latest football news via ESPN API (auto-scrolling gallery)
- Recent matches from top 5 leagues
- AI Insights: most in-form teams, best attack, best defence
- Player spotlight with AI-generated summary (rotates daily)
- Iconic moments photo gallery

### Live Scores (`/live`)
- Real-time scores from Premier League, La Liga, Serie A, Bundesliga, Ligue 1 + their domestic cups (FA Cup, Copa del Rey, Coppa Italia, DFB Pokal, Coupe de France) + UCL, UEL, UECL
- Filter by: All / Live / Upcoming / Finished
- Pulsing live indicator with current match minute
- Goal scorers shown below team names (with penalty/OG labels)
- Expandable match stats panel (possession, shots, corners, fouls)
- Auto-refreshes every 30 seconds

### Football Assistant (`/chat`)
Natural language queries routed to the right data source:
- **Squad lookup** — "show Arsenal squad" → football-data.org
- **Player stats** — "mbappe stats" → api-football.com (goals, assists, rating, trophies, transfer history)
- **Graph queries** — "who plays for Barcelona" → Neo4j
- **Nationality queries** — "show all Brazilian players in Premier League" → Neo4j
- **Position queries** — "which club has the most attackers" → ESPN roster API
- **Tactical/general** — "what is Real Madrid's playstyle" → Groq LLM

### Match Analysis (`/matches`)
1. Select competition (PL, La Liga, Serie A, Bundesliga, Ligue 1, Champions League)
2. Select season and team
3. Browse finished matches (paginated, 5 at a time)
4. Click a match for full detail:
   - Score, date, venue, formations, coaches
   - Goals timeline with scorers
   - Cards
   - Starting XIs
   - Match statistics (possession, shots, xG etc.)
   - AI tactical analysis via Groq

---

## Data Pipeline

```
User Query (Football Assistant)
    │
    ▼
analyze_query()  ←── keyword + pattern matching
    │
    ├── intent: api               → football-data.org   → squad data
    ├── intent: player_stats      → api-football.com    → goals, assists, trophies, transfers
    ├── intent: graph             → Neo4j               → squad / career queries
    ├── intent: graph_nationality → Neo4j               → nationality filters
    ├── intent: graph_analysis    → ESPN roster API     → position counts per club
    └── intent: llm               → Groq 120B           → tactics, opinions, comparisons

Dashboard Data
    ├── News          → ESPN unofficial API (/news per league)
    ├── Live Scores   → ESPN unofficial API (/scoreboard per competition)
    ├── Recent Matches → football-data.org
    ├── In-form teams  → football-data.org standings
    ├── Best attack/defence → football-data.org standings
    └── Player spotlight → Groq LLM (rotates by day of year)

Match Detail
    ├── Basic info (score, date, teams) → api-football.com
    ├── Goals, cards, lineups          → api-football.com
    ├── Match statistics               → api-football.com
    └── AI tactical analysis           → Groq LLM
```

---

## Graph Database (Neo4j)

Player and club data from CSV datasets loaded into Neo4j with:
- `(Player)-[:PLAYS_FOR]->(Club)` relationships
- `(Player)-[:HAS_NATIONALITY]->(Nation)` relationships
- Player properties: name, position, nationality, date of birth, market value

Enables queries that flat REST APIs can't do efficiently:
- All players of a specific nationality across all clubs
- Players who played for two specific clubs
- Squad composition by position
- Nationality diversity rankings

---

## API Sources

| Data | Source | Notes |
|---|---|---|
| League standings, recent matches | football-data.org | Free tier |
| Match detail, goals, lineups, stats | api-football.com | 100 req/day free |
| Player stats, trophies, transfers | api-football.com | 100 req/day free |
| Live scores, news, rosters | ESPN unofficial API | No key required |
| AI responses | Groq API | Free tier |
| Graph queries | Neo4j AuraDB | Free tier |

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install fastapi uvicorn requests python-dotenv neo4j openai httpx pandas
```

Create `backend/.env`:
```
FOOTBALL_API_KEY=your_football_data_org_key
API_FOOTBALL_KEY=your_api_football_key
GROQ_API_KEY=your_groq_key
NEO4J_URI=neo4j+s://your_instance
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

```bash
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## Running

```bash
# Terminal 1 — Backend
cd backend
venv\Scripts\activate
uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### Load Graph Database (one-time)
After starting the backend, POST to `http://localhost:8000/sync-all-squads` via the FastAPI docs at `/docs` to populate Neo4j with squad data.
