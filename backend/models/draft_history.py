from typing import List
from backend.models.players import Player
from backend.data.sqlite.database import read_draft_history, write_draft_history
#from backend.data.postgresql.main import read_postgres_draft_history, write_postgres_draft_history
from pydantic import BaseModel, Field
import os

#if os.getenv("DEPLOYMENT_ENVIRONMENT") == 'DEV':
#    use_local_db = True
#else: 
#    use_local_db = False
use_local_db = True

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
      #  if use_local_db:
        fields = read_draft_history(id.lower())
     #   else:
     #       fields = read_postgres_draft_history(id.lower())
        if not fields:
            from backend.models.draft import Draft
            items = await initialize_draft_history_items(id.lower())
            fields = {
                "draft_id": id.lower(),
                "items": [item.model_dump(by_alias=True) if hasattr(item, 'model_dump') else item for item in items]
            }
     #       if use_local_db:
            write_draft_history(id, fields)
    #        else:
    #            write_postgres_draft_history(id, fields)
        return cls(**fields)

    def update_draft_history(self, round: int, pick: int, selection: Player, rationale: str):
        history_item = next((item for item in self.items if item.round == round and item.pick==pick), None)
        if not history_item:
            print(f"History item not found for draft: {self.name}, round: {round}, pick: {pick}.")
            raise ValueError(f"History item not found for draft: {self.name}, round: {round}, pick: {pick}.")
        history_item.selection = selection.name
        history_item.rationale = rationale
        self.save()
    
    def save(self):
        data = self.model_dump(by_alias=True)
    #    if use_local_db:
        write_draft_history(self.draft_id.lower(), data)
    #    else:
    #        write_postgres_draft_history(self.draft_id.lower(), data)


async def initialize_draft_history_items(id: str) -> List[DraftHistoryItem]:
    from backend.models.draft import Draft
    draft = await Draft.get(id.lower())
    items = []
    current_pick = 1

    for round_num in range(1, draft.num_rounds + 1):
        draft_order = draft.get_draft_order(round_num)
        for team in draft_order:
            items.append(DraftHistoryItem(round=round_num, pick=current_pick, team=team.name, selection="", rationale=""))
            current_pick+=1
    return items       

    
        

    



