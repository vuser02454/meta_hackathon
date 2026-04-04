import os
import json
import time

from openai import OpenAI
from environment.env import LegalContractEnv
from environment.models import Action, ActionType

API_BASE_URL = os.environ.get("API_BASE_URL")
MODEL_NAME = os.environ.get("MODEL_NAME")
HF_TOKEN = os.environ.get("HF_TOKEN")

SYSTEM_PROMPT = """You are an expert legal contract reviewer.
Your objective is to review clauses and determine the appropriate action based on their contents.
Respond ONLY with a valid JSON object matching this schema:
{
  "action": "flag|redline|approve|escalate",
  "reason": "Brief reasoning",
  "suggested_edit": "Suggested edit text (if redlining) or null"
}"""

def parse_with_retry(client: OpenAI, response_text: str, current_clause: dict, retries: int = 1) -> dict:
    # Try cleaning markdown formats
    clean_text = response_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        data = json.loads(clean_text)
        # Validation
        if "action" not in data or data["action"] not in [a.value for a in ActionType]:
            raise ValueError(f"Invalid action: {data.get('action')}")
        if "reason" not in data:
             data["reason"] = "No reason provided"
        return data
    except Exception as e:
        if retries > 0:
            retry_prompt = f"Failed to parse JSON: {str(e)}. Please respond ONLY with a valid JSON object."
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Clause to review:\n\n{current_clause['text']}\n\nType: {current_clause['clause_type']}"},
                        {"role": "assistant", "content": response_text},
                        {"role": "user", "content": retry_prompt}
                    ],
                    temperature=0.0
                )
                return parse_with_retry(client, response.choices[0].message.content, current_clause, retries - 1)
            except Exception as api_err:
                return {"action": "escalate", "reason": f"Retry completely failed: {str(api_err)}", "suggested_edit": None}
        
        return {"action": "escalate", "reason": f"JSON parse failure fallback: {str(e)}", "suggested_edit": None}

def run_task(env: LegalContractEnv, task_id: str, client: OpenAI):
    state = env.reset(task_id)
    print(f"[START] task_id={task_id}")
    
    start_time = time.time()
    
    while not state.done:
        clause = state.current_clause.model_dump()
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Clause to review:\n\n{clause['text']}\n\nType: {clause['clause_type']}"}
                ],
                temperature=0.0
            )
            response_text = response.choices[0].message.content
            
            data = parse_with_retry(client, response_text, clause)
            
            action = Action(
                action=data["action"],
                clause_id=clause["id"],
                reason=data["reason"],
                suggested_edit=data.get("suggested_edit")
            )
        except Exception as e:
            action = Action(
                action=ActionType.escalate,
                clause_id=clause["id"],
                reason=f"API Request failed: {str(e)}",
                suggested_edit=None
            )
            
        state, reward, done = env.step(action)
        # Using action.action directly since use_enum_values=True in Pydantic models
        print(f"[STEP] clause={clause['id']} action={action.action} reward={reward:.2f}")
        
    score = env.grade()
    print(f"[END] task_id={task_id} score={score:.4f}")

def main():
    if not all([API_BASE_URL, MODEL_NAME, HF_TOKEN]):
         print("Warning: Missing API_BASE_URL, MODEL_NAME, or HF_TOKEN environment variables. Script may fail unless default values are present in OpenAI client.")
         
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN or "dummy_key"
    )
    
    env = LegalContractEnv()
    
    for task_id in ["task1", "task2", "task3"]:
        run_task(env, task_id, client)
        
if __name__ == "__main__":
    main()
