"""
Core environment logic for the Legal Contract Review OpenEnv environment.
"""

import json
import os
from pathlib import Path
from typing import Optional, Tuple

from environment.models import (
    Action, ActionType, Clause, Contract, EpisodeResult,
    ReviewEntry, RiskLevel, State
)


# ---------------------------------------------------------------------------
# Reward table  (ground_truth_risk_level → agent_action → reward)
# ---------------------------------------------------------------------------
REWARD_TABLE = {
    RiskLevel.high_risk: {
        ActionType.flag:     +1.0,
        ActionType.redline:  +0.7,
        ActionType.escalate: +0.5,
        ActionType.approve:  -1.0,
    },
    RiskLevel.safe: {
        ActionType.approve:  +0.3,
        ActionType.flag:     -0.3,
        ActionType.redline:  -0.2,
        ActionType.escalate: -0.1,
    },
    RiskLevel.ambiguous: {
        ActionType.escalate: +0.8,
        ActionType.flag:     +0.3,
        ActionType.redline:  +0.2,
        ActionType.approve:  -0.2,
    },
}

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent.parent
_CONTRACT_DIR = _BASE_DIR / "data" / "contracts"
_LABEL_DIR    = _BASE_DIR / "data" / "risk_labels"

_TASK_MAP = {
    "task1": ("nda_easy.json",    "nda_labels.json"),
    "task2": ("saas_medium.json", "saas_labels.json"),
    "task3": ("ma_hard.json",     "ma_labels.json"),
}


# ---------------------------------------------------------------------------
# Environment class
# ---------------------------------------------------------------------------
class LegalContractEnv:
    """
    OpenEnv-compatible environment for legal contract review.

    Usage:
        env = LegalContractEnv()
        state = env.reset("task1")
        while not state.done:
            action = agent.act(state)
            state, reward, done = env.step(action)
        score = env.grade()
    """

    def __init__(self) -> None:
        self._contract: Optional[Contract] = None
        self._labels: Optional[dict] = None
        self._state: Optional[State] = None
        self._clause_index: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, task_id: str) -> State:
        """Load a contract and return the initial State."""
        if task_id not in _TASK_MAP:
            raise ValueError(
                f"Unknown task_id '{task_id}'. Valid options: {list(_TASK_MAP)}"
            )

        contract_file, label_file = _TASK_MAP[task_id]
        self._contract = self._load_contract(_CONTRACT_DIR / contract_file)
        self._labels   = self._load_labels(_LABEL_DIR / label_file)

        self._clause_index = 0
        self._state = State(
            contract_id=self._contract.contract_id,
            task_id=task_id,
            current_clause=self._contract.clauses[0],
            step_number=0,
            total_clauses=len(self._contract.clauses),
            review_history=[],
            done=False,
            cumulative_reward=0.0,
        )
        return self._state

    def step(self, action: Action) -> Tuple[State, float, bool]:
        """
        Process an action and advance the environment by one clause.

        Returns:
            (next_state, reward, done)
        """
        if self._state is None or self._contract is None:
            raise RuntimeError("Call reset() before step().")
        if self._state.done:
            raise RuntimeError("Episode is already done. Call reset() to start a new one.")

        # Validate that the action targets the current clause
        current_clause = self._state.current_clause
        if action.clause_id != current_clause.id:
            raise ValueError(
                f"action.clause_id '{action.clause_id}' does not match "
                f"current clause '{current_clause.id}'."
            )

        # Compute reward
        ground_truth_risk = RiskLevel(self._labels[current_clause.id])
        reward = REWARD_TABLE.get(ground_truth_risk, {}).get(
            ActionType(action.action), 0.0
        )

        # Record in history
        entry = ReviewEntry(
            clause_id=action.clause_id,
            action=action.action,
            reason=action.reason,
            suggested_edit=action.suggested_edit,
            reward=reward,
        )
        self._state.review_history.append(entry)
        self._state.cumulative_reward += reward
        self._state.step_number += 1

        # Advance to next clause
        self._clause_index += 1
        if self._clause_index >= len(self._contract.clauses):
            self._state.done = True
            self._state.current_clause = None
        else:
            self._state.current_clause = self._contract.clauses[self._clause_index]

        return self._state, reward, self._state.done

    def state(self) -> State:
        """Return a snapshot of the current state (does not mutate)."""
        if self._state is None:
            raise RuntimeError("Call reset() first.")
        return self._state.model_copy(deep=True)

    def grade(self) -> float:
        """
        Run the appropriate grader and return a float score in [0, 1].
        Must be called after the episode is done.
        """
        if self._state is None or not self._state.done:
            raise RuntimeError("Episode is not finished. Complete all steps first.")

        task_id = self._state.task_id
        if task_id == "task1":
            from environment.graders.task1_nda import NDAGrader
            grader = NDAGrader(self._labels)
        elif task_id == "task2":
            from environment.graders.task2_saas import SaaSGrader
            grader = SaaSGrader(self._labels)
        elif task_id == "task3":
            from environment.graders.task3_ma import MAGrader
            grader = MAGrader(self._labels)
        else:
            raise ValueError(f"No grader for task_id '{task_id}'.")

        return grader.score(self._state.review_history)

    def episode_result(self) -> EpisodeResult:
        """Return a structured summary of the completed episode."""
        score = self.grade()
        return EpisodeResult(
            task_id=self._state.task_id,
            contract_id=self._state.contract_id,
            total_steps=self._state.step_number,
            cumulative_reward=self._state.cumulative_reward,
            grader_score=score,
            review_history=self._state.review_history,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_contract(path: Path) -> Contract:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return Contract(**data)

    @staticmethod
    def _load_labels(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
