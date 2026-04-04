"""
M&A Task Grader
"""
from typing import List
from environment.models import ReviewEntry, ActionType

class MAGrader:
    def __init__(self, labels: dict):
        self.labels = labels

    def score(self, history: List[ReviewEntry]) -> float:
        # risk_coverage × escalation_accuracy
        # risk_coverage: how many high_risk were flagged/redlined/escalated
        # escalation_accuracy: how many escalated were actually ambiguous
        
        high_risk_total = sum(1 for v in self.labels.values() if v == "high_risk")
        ambiguous_total = sum(1 for v in self.labels.values() if v == "ambiguous")
        
        ambiguous_escalated = 0
        total_escalated = 0
        high_risk_covered = 0
        
        for entry in history:
            ground_truth = self.labels.get(entry.clause_id)
            
            if entry.action == ActionType.escalate:
                total_escalated += 1
                if ground_truth == "ambiguous":
                    ambiguous_escalated += 1
                    
            if ground_truth == "high_risk" and entry.action in [ActionType.flag, ActionType.redline, ActionType.escalate]:
                high_risk_covered += 1
                
        coverage = high_risk_covered / high_risk_total if high_risk_total > 0 else 1.0
        
        if total_escalated == 0:
            accuracy = 1.0 if ambiguous_total == 0 else 0.0
        else:
            accuracy = ambiguous_escalated / total_escalated
            
        return float(coverage * accuracy)
