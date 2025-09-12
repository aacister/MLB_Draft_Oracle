from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import draft, player_pool, players, teams, draft_history
import os

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(draft.router, prefix="/v1")
app.include_router(player_pool.router, prefix="/v1") 
app.include_router(players.router, prefix="/v1") 
app.include_router(teams.router, prefix="/v1") 
app.include_router(draft_history.router, prefix="/v1") 


api_url = os.getenv("API_URL")
@app.get("/")
async def root():
    return {"message": "Welcome to the MLB Draft Oracle API!"}