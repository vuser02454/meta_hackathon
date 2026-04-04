"""
NDA Task Grader
"""
from typing import List
from environment.models import ReviewEntry, ActionType

class NDAGrader:
    def __init__(self, labels: dict):
        self.labels = labels
        self.total_high_risk = sum(1 for v in labels.values() if v == "high_risk")

    def score(self, history: List[ReviewEntry]) -> float:
        if self.total_high_risk == 0:
            return 1.0
        
        correct_flags = 0
        for entry in history:
            ground_truth = self.labels.get(entry.clause_id)
            if ground_truth == "high_risk" and entry.action in [ActionType.flag, ActionType.redline, ActionType.escalate]:
                # Any form of identifying it as a risk counts as a correct flag for the easy task
                correct_flags += 1
                
        return min(1.0, correct_flags / self.total_high_risk)
