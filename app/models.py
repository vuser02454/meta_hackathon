from typing import Optional
from pydantic import BaseModel, Field

class CurrentClause(BaseModel):
    id: str = Field(..., description="Unique clause ID")
    text: str = Field(..., description="The textual content of the clause")
    category: str = Field(..., description="The legal category of the clause")

class ActionParams(BaseModel):
    action: str = Field(..., description="Action to take: flag, redline, escalate, synthesize")

class State(BaseModel):
    task_id: str = Field(..., description="The current task identifier: nda_review, saas_review, ma_review")
    current_clause: Optional[CurrentClause] = Field(None, description="The struct of the current clause")
    clauses_reviewed: int = Field(default=0, description="The number of clauses reviewed so far")
    total_clauses: int = Field(default=0, description="The total number of clauses for this task")
    cumulative_reward: float = Field(default=0.0, description="Cumulative reward accumulated 0.0 to 1.0")
    flags_raised: list[str] = Field(default_factory=list, description="A list of clauses flagged by the agent")
    done: bool = Field(default=False, description="Indicates if the episode has finished")
