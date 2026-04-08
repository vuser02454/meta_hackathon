import os
import json
import time
import psutil
from openai import OpenAI
from app.environment import LegalContractEnv
from app.models import ActionParams
from app.graders import Grader

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: str) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# Hard Constraints
API_BASE_URL = os.environ.get("API_BASE_URL", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

def get_memory_mb():
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)

def run_task(env: LegalContractEnv, task_id: str, client: OpenAI):
    state = env.reset(task_id)

    log_start(task=task_id, env="legal_evaluation", model=MODEL_NAME)
    rewards = []


    task_start_time = time.time()

    while not state.done:
        # ✅ Time constraint (20 min per task)
        if time.time() - task_start_time > 1200:
            break

        # ✅ Memory constraint (8GB)
        if get_memory_mb() > 8192:
            break

        clause_text = state.current_clause.get("text", "") if isinstance(state.current_clause, dict) else (state.current_clause.text if state.current_clause else "")

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
        rewards.append(reward)

        log_step(step=state.clauses_reviewed, action=action_choice, reward=reward, done=done, error=None)

    grader = Grader()
    final_score = grader.score(state)
    success = final_score >= 0.5
    
    log_end(success=success, steps=state.clauses_reviewed, score=final_score, rewards=rewards)

    return final_score, state.clauses_reviewed


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "dummy-key")
    env = LegalContractEnv()

    tasks = ["nda_review", "saas_review", "ma_review"]

    for task in tasks:
        final_score, total_steps = run_task(env, task, client)

    # Optional memory print (outside structured logs) removed for stdout sanity


if __name__ == "__main__":
    main()