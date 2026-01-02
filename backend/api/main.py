from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api import draft, player_pool, players, teams, draft_history
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

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


@app.get("/health")
def health_check():
    """Health check MLB Draft Oracle API"""
    return {"status": "healthy"}

if os.getenv("DEPLOYMENT_ENVIRONMENT") != "LAMBDA":
    static_path = Path("static")
    if static_path.exists():
        @app.get("/")
        async def serve_root():
            return FileResponse(static_path / "index.html")
        
        app.mount("/", StaticFiles(directory="static", html=True), name="static")
