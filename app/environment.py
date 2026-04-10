from typing import Tuple, Dict, Any
import os
import sys

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .models import State, ActionParams

class LegalContractEnv:
    def __init__(self):
        self.state: State = None
        self.task_configs = {
            "nda_review": {"steps": 10},
            "saas_review": {"steps": 15},
            "ma_review": {"steps": 20}
        }
        self.action_rewards = {
            "flag": 0.2,
            "redline": 0.3,
            "escalate": 0.25,
            "synthesize": 0.4
        }
    
    def reset(self, task_id: str) -> State:
        if task_id not in self.task_configs:
            raise ValueError(f"Task '{task_id}' is not supported. Use nda_review, saas_review, or ma_review.")
            
        total_steps = self.task_configs[task_id]["steps"]
        
        self.state = State(
            task_id=task_id,
            current_clause={"id": "clause_0", "text": f"Sample clause 1 of {task_id}", "category": "general"},
            clauses_reviewed=0,
            total_clauses=total_steps,
            cumulative_reward=0.0,
            flags_raised=[],
            done=False
        )
        self.raw_cumulative_reward = 0.0
        return self.state

    def step(self, action_params: ActionParams) -> Tuple[State, float, bool]:
        if self.state is None or self.state.done:
            raise RuntimeError("Environment is not initialized or episode is already done.")

        action = action_params.action.lower()
        
        # Calculate Reward based on exact prompt constraints
        raw_reward = self.action_rewards.get(action, 0.0)
        
        # Track specific flag logic
        if action in ["flag", "redline", "escalate"]:
            if self.state.current_clause and "id" in self.state.current_clause:
                self.state.flags_raised.append(self.state.current_clause["id"])
            
        self.state.cumulative_reward += raw_reward
        
        # Advance Step
        self.state.clauses_reviewed += 1
        
        # Normalize reward from 0.0 to 1.0 safely
        normalized_reward = raw_reward / 1.0 # The step reward is already <= 1.0
        
        self.raw_cumulative_reward = getattr(self, "raw_cumulative_reward", 0.0) + raw_reward
        self.state.cumulative_reward = min(1.0, self.raw_cumulative_reward / (self.state.total_clauses * 0.4))
        
        if self.state.clauses_reviewed >= self.state.total_clauses:
            self.state.done = True
            self.state.current_clause = None
        else:
            self.state.current_clause = {
                "id": f"clause_{self.state.clauses_reviewed}",
                "text": f"Sample clause {self.state.clauses_reviewed + 1} of {self.state.task_id}",
                "category": "legal"
            }

        return self._get_state_copy(), raw_reward, self.state.done

    def _get_state_copy(self) -> State:
        return self.state.model_copy(deep=True)
