from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api import draft, draft_async, player_pool, players, teams, draft_history, admin
import os
from dotenv import load_dotenv, find_dotenv
import logging

load_dotenv(override=True, dotenv_path=find_dotenv())

logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "http://mlbdraftoracle-frontend-425865275846.s3-website.us-east-2.amazonaws.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "*"  # Keep wildcard as fallback
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


app.include_router(draft.router, prefix="/v1")
app.include_router(draft_async.router, prefix="/v1") 
app.include_router(player_pool.router, prefix="/v1") 
app.include_router(players.router, prefix="/v1") 
app.include_router(teams.router, prefix="/v1") 
app.include_router(draft_history.router, prefix="/v1") 
app.include_router(admin.router, prefix="/v1")


@app.get("/health")
def health_check():
    """Health check MLB Draft Oracle API"""
    return {"status": "healthy"}

# Handle OPTIONS requests for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight"""
    return {}

if os.getenv("DEPLOYMENT_ENVIRONMENT") != "LAMBDA":
    static_path = Path("static")
    if static_path.exists():
        @app.get("/")
        async def serve_root():
            return FileResponse(static_path / "index.html")
        
        app.mount("/", StaticFiles(directory="static", html=True), name="static")