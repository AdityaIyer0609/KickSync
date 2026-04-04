from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import teams, players, transfers, chat, agent, matches, dashboard

app = FastAPI()

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
