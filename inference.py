import os
import json
import time
import psutil
from openai import OpenAI
from app.environment import LegalContractEnv
from app.models import ActionParams
from app.graders import Grader

# Hard Constraints
API_BASE_URL = os.environ.get("API_BASE_URL", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

def get_memory_mb():
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)

def run_task(env: LegalContractEnv, task_id: str, client: OpenAI):
    state = env.reset(task_id)

    # ✅ START LOG (STRICT FORMAT)
    print("\n[START]")
    print(json.dumps({
        "task_id": task_id,
        "total_clauses": state.total_clauses,
        "timestamp": time.time()
    }))

    task_start_time = time.time()

    while not state.done:
        # ✅ Time constraint (20 min per task)
        if time.time() - task_start_time > 1200:
            break

        # ✅ Memory constraint (8GB)
        if get_memory_mb() > 8192:
            break

        clause_text = state.current_clause["text"]

        prompt = f"""
Review the following legal clause and respond ONLY in JSON format:
{{"action": "flag|redline|escalate|synthesize"}}

Clause:
{clause_text}
"""

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a legal AI checker."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw_output = response.choices[0].message.content.strip()
            cleaned = raw_output.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            action_choice = data.get("action", "flag").lower()

        except Exception:
            action_choice = "flag"

        # ✅ Enforce allowed actions
        if action_choice not in ["flag", "redline", "escalate", "synthesize"]:
            action_choice = "flag"

        action = ActionParams(action=action_choice)
        state, reward, done = env.step(action)

        # ✅ STEP LOG (STRICT FORMAT)
        print("\n[STEP]")
        print(json.dumps({
            "task_id": task_id,
            "step": state.clauses_reviewed,
            "action": action_choice,
            "clause_id": state.current_clause["id"],
            "reward": reward,
            "cumulative_reward": state.cumulative_reward,
            "done": done
        }))

    grader = Grader()
    final_score = grader.score(state)

    return final_score, state.clauses_reviewed


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "dummy-key")
    env = LegalContractEnv()

    tasks = ["nda_review", "saas_review", "ma_review"]

    for task in tasks:
        final_score, total_steps = run_task(env, task, client)

        # ✅ END LOG (STRICT FORMAT)
        print("\n[END]")
        print(json.dumps({
            "task_id": task,
            "total_steps": total_steps,
            "final_score": final_score,
            "timestamp": time.time()
        }))

    # Optional memory print (outside structured logs)
    print(f"\nMemory usage: {get_memory_mb()} MB")


if __name__ == "__main__":
    main()