from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api import draft, player_pool, players, teams, draft_history
import os
from dotenv import load_dotenv

load_dotenv(override=True)

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


# api_url = os.getenv("API_URL")
# @app.get("/")
# async def root():
#    return {"message": "Welcome to the MLB Draft Oracle API!"}

@app.get("/health")
def health_check():
    """Health check MLB Draft Oracle API"""
    return {"status": "healthy"}

# Serve static files (our Next.js export) - MUST BE LAST!
static_path = Path("static")
if static_path.exists():
    # Serve index.html for the root path
    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")
    
    # Mount static files for all other routes
    app.mount("/", StaticFiles(directory="static", html=True), name="static")