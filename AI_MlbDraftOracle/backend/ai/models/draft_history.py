from typing import List
from ai.models.players import Player
from ai.data.database import read_draft_history, write_draft_history
from pydantic import BaseModel, Field

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
        fields = read_draft_history(id.lower())
        if not fields:
            from ai.models.draft import Draft
            items = await initialize_draft_history_items(id.lower())
            fields = {
                "draft_id": id.lower(),
                "items": [item.model_dump(by_alias=True) if hasattr(item, 'model_dump') else item for item in items]
            }
            write_draft_history(id, fields)
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
        write_draft_history(self.draft_id.lower(), data)


async def initialize_draft_history_items(id: str) -> List[DraftHistoryItem]:
    from ai.models.draft import Draft
    draft = await Draft.get(id.lower())
    items = []
    current_pick = 1

    for round_num in range(1, draft.num_rounds + 1):
        draft_order = draft.get_draft_order(round_num)
        for team in draft_order:
            items.append(DraftHistoryItem(round=round_num, pick=current_pick, team=team.name, selection="", rationale=""))
            current_pick+=1
    return items       

    
        

    



