from typing import List
from backend.models.players import Player
from backend.data.postgresql.unified_db import read_draft_history, write_draft_history
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class DraftHistoryItem(BaseModel):
    round: int
    pick: int
    team: str
    selection: str
    rationale: str

class DraftHistory(BaseModel):
    draft_id: str = Field(description="Id of the draft.")
    items: List[DraftHistoryItem] = Field(description="List of draft history items.")

    @classmethod
    async def get(cls, id: str):
        """Get draft history from PostgreSQL RDS only"""
        logger.info(f"Loading draft history for {id} from PostgreSQL RDS")
        fields = read_draft_history(id.lower())
        if not fields:
            from backend.models.draft import Draft
            items = await initialize_draft_history_items(id.lower())
            fields = {
                "draft_id": id.lower(),
                "items": [item.model_dump(by_alias=True) if hasattr(item, 'model_dump') else item for item in items]
            }
            write_draft_history(id, fields)
            logger.info(f"Initialized draft history for {id} in PostgreSQL RDS")
        return cls(**fields)

    def update_draft_history(self, round: int, pick: int, selection: Player, rationale: str):
        """Update draft history in PostgreSQL RDS"""
        history_item = next((item for item in self.items if item.round == round and item.pick==pick), None)
        if not history_item:
            error_msg = f"History item not found for draft: {self.draft_id}, round: {round}, pick: {pick}."
            logger.error(error_msg)
            raise ValueError(error_msg)
        history_item.selection = selection.name
        history_item.rationale = rationale
        self.save()
        logger.info(f"Updated draft history for {self.draft_id} in PostgreSQL RDS")
    
    def save(self):
        """Save draft history to PostgreSQL RDS"""
        data = self.model_dump(by_alias=True)
        write_draft_history(self.draft_id.lower(), data)
        logger.debug(f"Saved draft history for {self.draft_id} to PostgreSQL RDS")


async def initialize_draft_history_items(id: str) -> List[DraftHistoryItem]:
    """Initialize draft history items for a new draft"""
    from backend.models.draft import Draft
    draft = await Draft.get(id.lower())
    items = []
    current_pick = 1

    for round_num in range(1, draft.num_rounds + 1):
        draft_order = draft.get_draft_order(round_num)
        for team in draft_order:
            items.append(DraftHistoryItem(round=round_num, pick=current_pick, team=team.name, selection="", rationale=""))
            current_pick+=1
    
    logger.info(f"Initialized {len(items)} draft history items for draft {id}")
    return items