import os
import json
import sys
from unittest.mock import MagicMock

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

from environment.env import LegalContractEnv
from environment.models import ActionType
import inference

def run_mock_verification():
    # Mock the OpenAI client
    mock_client = MagicMock()

    # Sequence of mock responses for Task 1 (8 clauses)
    # We will alternate actions to see different rewards
    responses = [
        {"action": "approve", "reason": "Safe clause", "suggested_edit": None}, # c1: safe -> +0.3
        {"action": "approve", "reason": "Safe clause", "suggested_edit": None}, # c2: safe -> +0.3
        {"action": "flag",    "reason": "High risk",   "suggested_edit": None}, # c3: high_risk -> +1.0
        {"action": "approve", "reason": "Safe clause", "suggested_edit": None}, # c4: safe -> +0.3
        {"action": "approve", "reason": "Safe clause", "suggested_edit": None}, # c5: high_risk -> -1.0
        {"action": "flag",    "reason": "False flag",  "suggested_edit": None}, # c6: safe -> -0.3
        {"action": "approve", "reason": "Safe clause", "suggested_edit": None}, # c7: safe -> +0.3
        {"action": "approve", "reason": "Safe clause", "suggested_edit": None}, # c8: safe -> +0.3
    ]
    
    mock_responses = []
    for r in responses:
        m = MagicMock()
        m.choices = [MagicMock(message=MagicMock(content=json.dumps(r)))]
        mock_responses.append(m)
    
    mock_client.chat.completions.create.side_effect = mock_responses

    # Run Task 1 (NDA Easy)
    env = LegalContractEnv()
    print("--- Verifying Output Format for Task 1 ---")
    inference.run_task(env, "task1", mock_client)

if __name__ == "__main__":
    run_mock_verification()
