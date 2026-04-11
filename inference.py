import os
import json
import time
import psutil
from openai import OpenAI

# ── FIX: Import path consistency ──────────────────────────────────────────────
# Before: from server.environment / from server.graders  (mismatched with repo)
# After:  from app.environment    / from app.graders     (matches GitHub app/ folder)
from app.environment import LegalContractEnv
from app.models import ActionParams
from app.graders import Grader

# ── Hard Constraints ──────────────────────────────────────────────────────────
API_BASE_URL     = os.environ.get("API_BASE_URL", "")
MODEL_NAME       = os.environ.get("MODEL_NAME", "gpt-4")
HF_TOKEN         = os.environ.get("HF_TOKEN", "")

MAX_TASK_SECONDS = 1100
MAX_MEMORY_MB    = 7800
ALLOWED_ACTIONS  = {"flag", "redline", "escalate", "approve"}

# ── FIX: High-risk keyword override ──────────────────────────────────────────
HIGH_RISK_KEYWORDS = {
    "unlimited", "unconditional", "indemnif", "liable for all",
    "no liability cap", "sole discretion", "irrevocable",
    "waive all", "perpetual", "assign without consent",
    "unilateral", "without notice", "gross negligence",
}

# ── FIX: Task-aware token budget ──────────────────────────────────────────────
TOKEN_MAP = {
    "nda_review":  250,
    "saas_review": 300,
    "ma_review":   420,
}

# ── FIX: Boilerplate awareness ────────────────────────────────────────────────
STANDARD_BOILERPLATE = [
    "governing law", "entire agreement", "severability",
    "counterparts", "notices", "force majeure",
    "headings", "amendment procedure",
]

CONTRACT_MAP = {
    "nda_review":  "Non-Disclosure Agreement (NDA)",
    "saas_review": "SaaS Software License Agreement",
    "ma_review":   "Mergers & Acquisitions Term Sheet",
}

# ── Structured Loggers ────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: str = None) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: list) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior legal contract reviewer with 15 years of experience
across NDAs, SaaS agreements, and M&A transactions.

ACTION DEFINITIONS:
- approve  : Clause is standard and safe. No changes needed.
- flag     : Clause contains significant legal risk that must be highlighted.
- redline  : Clause is problematic and must be rewritten. Provide a safer version.
- escalate : Clause is too complex or ambiguous. Escalate to senior partner.

RISK SIGNALS — always flag or escalate these:
- Unlimited or uncapped liability exposure
- Unilateral termination with no notice period
- Broad indemnification with no carve-outs
- IP ownership transferring to counterparty
- Auto-renewal clauses with no opt-out window
- Data sharing without consent requirements
- Clauses with: irrevocable, unconditional, sole discretion, waive all

STANDARD BOILERPLATE — almost always approve:
- Governing law, Entire agreement, Severability
- Counterparts, Notices, Force majeure, Headings
- Amendment procedure requiring written consent

SCORING AWARENESS:
- Approving a high-risk clause = heavy penalty
- Missing a risk (false negative) = heavy penalty
- Over-flagging safe clauses = moderate penalty
- Correct escalation of ambiguous clauses = bonus

Always respond ONLY in valid JSON. No text outside the JSON block."""

# ── Build Prompt ──────────────────────────────────────────────────────────────
def build_prompt(
    clause_text: str,
    clause_category: str,
    task_id: str,
    clauses_reviewed: int,
    total_clauses: int,
    flags_raised: list,
    recent_history: list,
    is_ambiguous: bool = False,
) -> str:
    contract_type = CONTRACT_MAP.get(task_id, task_id)

    history_str = (
        "\n".join(
            f"  Clause {h['clause_id']}: {h['action'].upper()} — {h['reason']}"
            for h in recent_history[-3:]
        )
        if recent_history
        else "  None yet — this is your first clause."
    )

    ambiguity_hint = (
        "\n⚠️  NOTE: This clause is intentionally ambiguous. Consider escalating."
        if is_ambiguous else ""
    )

    return f"""CONTRACT TYPE : {contract_type}
PROGRESS      : Clause {clauses_reviewed + 1} of {total_clauses}
CLAUSE TYPE   : {clause_category}
FLAGGED SO FAR: {', '.join(flags_raised) if flags_raised else 'None'}
{ambiguity_hint}

YOUR LAST 3 DECISIONS:
{history_str}

STANDARD BOILERPLATE (approve unless clearly one-sided):
{', '.join(STANDARD_BOILERPLATE)}

CLAUSE TO REVIEW:
\"\"\"{clause_text}\"\"\"

REVIEW STEPS:
1. Is this clause type in the RISK SIGNALS list?
2. Is this standard boilerplate? Lean toward approve.
3. Is this clause ambiguous? Consider escalate.
4. Be consistent with your recent decisions above.
5. Choose: approve / flag / redline / escalate
6. Write a one-sentence reason.
7. If redline, rewrite the clause to remove the risk.

Respond ONLY in this JSON — nothing outside the braces:
{{
  "action": "approve|flag|redline|escalate",
  "reason": "one sentence explaining your decision",
  "suggested_edit": "rewritten clause if redline, otherwise null"
}}"""

# ── Risk Override ─────────────────────────────────────────────────────────────
def apply_risk_override(action: str, clause_text: str) -> str:
    if action == "approve":
        text_lower = clause_text.lower()
        for keyword in HIGH_RISK_KEYWORDS:
            if keyword in text_lower:
                return "flag"
    return action

# ── Memory Helper ─────────────────────────────────────────────────────────────
def get_memory_mb() -> float:
    return psutil.Process().memory_info().rss / (1024 * 1024)

# ── LLM Call with Retry ───────────────────────────────────────────────────────
def call_llm(client: OpenAI, prompt: str, task_id: str, retry: bool = True) -> dict:
    max_tokens = TOKEN_MAP.get(task_id, 300)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        raw     = response.choices[0].message.content.strip()
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        start = cleaned.find("{")
        end   = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]

        return json.loads(cleaned)

    except json.JSONDecodeError:
        if retry:
            return call_llm(
                client,
                prompt + "\n\nWARNING: Invalid JSON. Reply ONLY with the JSON object.",
                task_id,
                retry=False,
            )
        return {"action": "flag", "reason": "JSON parse error fallback", "suggested_edit": None}

    except Exception as e:
        return {"action": "flag", "reason": f"API error ({type(e).__name__}) fallback", "suggested_edit": None}

# ── Run Single Task ───────────────────────────────────────────────────────────
def run_task(env: LegalContractEnv, task_id: str, client: OpenAI) -> tuple:
    state      = env.reset(task_id)
    rewards    = []
    history    = []
    task_start = time.time()

    log_start(task=task_id, env="legal_evaluation", model=MODEL_NAME)

    while not state.done:

        if time.time() - task_start > MAX_TASK_SECONDS:
            log_step(state.clauses_reviewed, "approve", 0.0, True, "timeout")
            break

        if get_memory_mb() > MAX_MEMORY_MB:
            log_step(state.clauses_reviewed, "approve", 0.0, True, "memory_limit")
            break

        clause       = state.current_clause
        clause_text  = clause.text if clause else ""
        clause_id    = clause.id if clause else f"clause_{state.clauses_reviewed}"
        clause_cat   = clause.category if clause else "unknown"
        is_ambiguous = clause.is_ambiguous if clause else False

        prompt = build_prompt(
            clause_text      = clause_text,
            clause_category  = clause_cat,
            task_id          = task_id,
            clauses_reviewed = state.clauses_reviewed,
            total_clauses    = state.total_clauses,
            flags_raised     = state.flags_raised,
            recent_history   = history,
            is_ambiguous     = is_ambiguous,
        )

        data           = call_llm(client, prompt, task_id)
        action_choice  = data.get("action", "flag").lower().strip()
        reason         = data.get("reason", "no reason provided")
        suggested_edit = data.get("suggested_edit", None)

        if action_choice not in ALLOWED_ACTIONS:
            action_choice = "flag"

        action_choice = apply_risk_override(action_choice, clause_text)

        action              = ActionParams(
            action         = action_choice,
            reason         = reason,
            suggested_edit = suggested_edit,
        )
        state, reward, done = env.step(action)
        rewards.append(reward)

        history.append({
            "clause_id": clause_id,
            "action":    action_choice,
            "reason":    reason,
        })

        log_step(
            step   = state.clauses_reviewed,
            action = action_choice,
            reward = reward,
            done   = done,
        )

    grader      = Grader()
    final_score = grader.score(state)
    success     = final_score >= 0.5

    log_end(
        success = success,
        steps   = state.clauses_reviewed,
        score   = final_score,
        rewards = rewards,
    )

    return final_score, state.clauses_reviewed

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    client = OpenAI(
        base_url = API_BASE_URL or None,
        api_key  = HF_TOKEN or "dummy-key",
    )
    env   = LegalContractEnv()
    tasks = ["nda_review", "saas_review", "ma_review"]

    all_scores = []
    for task in tasks:
        try:
            score, steps = run_task(env, task, client)
            all_scores.append(score)
        except Exception as e:
            print(f"[ERROR] task={task} error={type(e).__name__}: {e}", flush=True)
            all_scores.append(0.0)

    if all_scores:
        avg = sum(all_scores) / len(all_scores)
        print(f"[SUMMARY] tasks={len(tasks)} avg_score={avg:.3f} scores={','.join(f'{s:.3f}' for s in all_scores)}", flush=True)

if __name__ == "__main__":
    main()
