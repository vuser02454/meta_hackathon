"""
Pydantic data models for the Legal Contract Review environment.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    safe = "safe"
    ambiguous = "ambiguous"
    high_risk = "high_risk"


class ClauseType(str, Enum):
    # NDA clause types
    confidentiality = "confidentiality"
    liability = "liability"
    term = "term"
    # SaaS clause types
    ip_ownership = "ip_ownership"
    data_privacy = "data_privacy"
    sla_penalty = "sla_penalty"
    payment = "payment"
    termination = "termination"
    # M&A clause types
    indemnity = "indemnity"
    jurisdiction = "jurisdiction"
    liability_cap = "liability_cap"
    representations = "representations"
    # Generic
    general = "general"


class ActionType(str, Enum):
    flag = "flag"
    redline = "redline"
    approve = "approve"
    escalate = "escalate"


class Clause(BaseModel):
    id: str = Field(..., description="Unique identifier for the clause")
    text: str = Field(..., description="Full text of the clause")
    clause_type: ClauseType = Field(..., description="Type/category of the clause")
    risk_level: Optional[RiskLevel] = Field(
        default=None,
        description="Risk level (only revealed in ground-truth labels, not to the agent)"
    )

    class Config:
        use_enum_values = True


class Action(BaseModel):
    action: ActionType = Field(
        ...,
        description="One of: flag, redline, approve, escalate"
    )
    clause_id: str = Field(..., description="ID of the clause being acted upon")
    reason: str = Field(..., description="Reasoning behind the action")
    suggested_edit: Optional[str] = Field(
        default=None,
        description="Suggested replacement text (required if action is 'redline')"
    )

    class Config:
        use_enum_values = True


class ReviewEntry(BaseModel):
    clause_id: str
    action: ActionType
    reason: str
    suggested_edit: Optional[str] = None
    reward: float = 0.0

    class Config:
        use_enum_values = True


class State(BaseModel):
    contract_id: str = Field(..., description="Unique contract identifier")
    task_id: str = Field(..., description="Task identifier (task1/task2/task3)")
    current_clause: Optional[Clause] = Field(
        default=None, description="The clause currently under review"
    )
    step_number: int = Field(default=0, description="Current step in the review loop")
    total_clauses: int = Field(default=0, description="Total number of clauses in contract")
    review_history: List[ReviewEntry] = Field(
        default_factory=list,
        description="History of all actions taken so far"
    )
    done: bool = Field(default=False, description="Whether the review is complete")
    cumulative_reward: float = Field(default=0.0, description="Accumulated reward so far")

    class Config:
        use_enum_values = True


class Contract(BaseModel):
    contract_id: str
    task_id: str
    title: str
    parties: List[str]
    clauses: List[Clause]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskInfo(BaseModel):
    task_id: str
    name: str
    difficulty: str
    description: str
    num_clauses: int
    num_high_risk: int


class EpisodeResult(BaseModel):
    task_id: str
    contract_id: str
    total_steps: int
    cumulative_reward: float
    grader_score: float
    review_history: List[ReviewEntry]
