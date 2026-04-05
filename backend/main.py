from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading

from routes import teams, players, transfers, chat, agent, matches, dashboard

def _warmup():
    """Pre-populate ESPN teams cache in background on startup."""
    try:
        from routes.agent import _get_all_espn_teams
        _get_all_espn_teams()
        print("✅ ESPN teams cache warmed up")
    except Exception as e:
        print(f"⚠️ ESPN warmup failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warmup, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Backend is running 🚀"}


app.include_router(teams.router)
app.include_router(players.router)
app.include_router(transfers.router)
app.include_router(chat.router)
app.include_router(agent.router)
app.include_router(matches.router)
app.include_router(dashboard.router)
