from typing import Optional
from pydantic import BaseModel, Field


# ── Clause ────────────────────────────────────────────────────────────────────
class Clause(BaseModel):
    id:           str  = Field(...,         description="Unique clause identifier e.g. clause_01")
    text:         str  = Field(...,         description="Full text of the legal clause")
    category:     str  = Field(...,         description="Clause type: liability | IP | indemnity | payment | termination | confidentiality | boilerplate")
    risk_level:   str  = Field("low",       description="Planted risk level: low / medium / high")
    is_ambiguous: bool = Field(False,       description="True if clause is intentionally ambiguous")


# ── Action ────────────────────────────────────────────────────────────────────
class ActionParams(BaseModel):
    action:         str            = Field(...,  description="Agent decision: approve | flag | redline | escalate")
    reason:         str            = Field("",   description="One-sentence justification for the action")
    suggested_edit: Optional[str]  = Field(None, description="Rewritten clause text when action is redline, else null")


# ── State ─────────────────────────────────────────────────────────────────────
class State(BaseModel):
    task_id:           str              = Field(...,               description="Current task: nda_review | saas_review | ma_review")
    current_clause:    Optional[Clause] = Field(None,             description="The clause currently under review")
    clauses_reviewed:  int              = Field(0,                description="Number of clauses processed so far")
    total_clauses:     int              = Field(0,                description="Total clauses in this contract")
    cumulative_reward: float            = Field(0.0,              description="Running reward total for this episode")
    flags_raised:      list[str]        = Field(default_factory=list, description="IDs of HIGH-RISK clauses correctly flagged by agent")
    escalations:       list[str]        = Field(default_factory=list, description="IDs of clauses escalated by agent")
    false_approvals:   list[str]        = Field(default_factory=list, description="IDs of high-risk clauses incorrectly approved")
    # NEW: track medium-risk flags and all high-risk clause IDs for grader ground truth
    medium_flags:      list[str]        = Field(default_factory=list, description="IDs of MEDIUM-RISK clauses correctly flagged by agent")
    all_high_risk_ids: list[str]        = Field(default_factory=list, description="Ground truth: all high-risk clause IDs in this episode")
    done:              bool             = Field(False,            description="True when episode has ended")
