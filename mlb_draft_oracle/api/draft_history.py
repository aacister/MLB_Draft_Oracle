from fastapi import HTTPException
from typing import List
from pydantic import BaseModel as PydanticBaseModel
from models.draft_history import DraftHistory, DraftHistoryItem
from fastapi import APIRouter
import os

api_url = os.getenv("API_URL")

router = APIRouter()

class DraftHistoryItemResponse(PydanticBaseModel):
    round: int
    pick: int
    team: str
    selection: str
    rationale: str

    class Config:
        from_attributes = True

class DraftHistoryResponse(PydanticBaseModel):
    draft_id: str
    items: List[DraftHistoryItemResponse]


@router.get('/draft-history/{draft_id}', response_model=DraftHistoryResponse)
async def get_draft_history(draft_id: str):
    draft_history = await DraftHistory.get(draft_id.lower())
    if not draft_history:
        raise HTTPException(status_code=404, detail="Draft history not found")
    
    return DraftHistoryResponse(
        draft_id=draft_history.draft_id,
        items=[
            DraftHistoryItemResponse(
                round=item.round,
                pick=item.pick,
                team=item.team,
                selection=item.selection,
                rationale=item.rationale
            ) for item in draft_history.items
        ]
    )