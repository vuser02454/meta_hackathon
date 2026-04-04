"""
SaaS Task Grader
"""
from typing import List
from environment.models import ReviewEntry, ActionType

class SaaSGrader:
    def __init__(self, labels: dict):
        self.labels = labels

    def score(self, history: List[ReviewEntry]) -> float:
        # Weighted F1 on risk detection
        true_pos = 0
        false_pos = 0
        false_neg = sum(1 for v in self.labels.values() if v == "high_risk")
        
        for entry in history:
            ground_truth = self.labels.get(entry.clause_id)
            is_detected = entry.action in [ActionType.flag, ActionType.redline, ActionType.escalate]
            
            if is_detected:
                if ground_truth == "high_risk":
                    true_pos += 1
                    false_neg -= 1
                else:
                    false_pos += 1
                    
        precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0.0
        recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0.0
        
        if precision + recall == 0:
            return 0.0
            
        f1 = 2 * (precision * recall) / (precision + recall)
        return float(f1)
