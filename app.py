import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
from models.draft import Draft
from models.player_pool import PlayerPool

async def main():
    draft = await Draft.get(id=None)
    player_pool = await PlayerPool.get(id=None)
    await draft.run(player_pool.id)

if __name__ == "__main__":
    print(f"Starting MLB Draft Oracle simulated draft...")
    process = asyncio.run(main())
