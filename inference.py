import os
import json
import time
import psutil
from openai import OpenAI
from server.environment import LegalContractEnv
from models import ActionParams, State
from server.graders import Grader

# ── Hard Constraints ─────────────────────────────────────────────────────────
API_BASE_URL     = os.environ.get("API_BASE_URL", "")
MODEL_NAME       = os.environ.get("MODEL_NAME", "gpt-4")
HF_TOKEN         = os.environ.get("HF_TOKEN", "")

MAX_TASK_SECONDS = 1100    # ~18.3 min — buffer under 20 min limit
MAX_MEMORY_MB    = 7800    # buffer under 8 GB limit
ALLOWED_ACTIONS  = {"flag", "redline", "escalate", "approve"}

# ── FIX 1: Never auto-approve high-risk clause types ─────────────────────────
HIGH_RISK_KEYWORDS = {
    "unlimited", "unconditional", "indemnif", "liable for all",
    "no liability cap", "sole discretion", "irrevocable",
    "waive all", "perpetual", "assign without consent",
    "unilateral", "without notice", "gross negligence",
}

# ── FIX 2: Scale max_tokens by task complexity ────────────────────────────────
TOKEN_MAP = {
    "nda_review":  250,   # short, simple clauses
    "saas_review": 300,   # medium complexity
    "ma_review":   420,   # complex clauses need more reasoning room
}

# ── FIX 3: Boilerplate clause types to almost always approve ─────────────────
STANDARD_BOILERPLATE = [
    "governing law", "entire agreement", "severability",
    "counterparts", "notices", "waiver of jury trial",
    "force majeure", "headings", "amendment procedure",
]

# ── Contract Type Map ─────────────────────────────────────────────────────────
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
- redline  : Clause is problematic and needs to be rewritten. Provide a safer version.
- escalate : Clause is too complex or ambiguous for junior review. Escalate to senior partner.

RISK SIGNALS — always flag or escalate these:
- Unlimited or uncapped liability exposure
- Unilateral termination with no notice period
- Broad indemnification with no carve-outs
- IP ownership transferring to the counterparty
- Auto-renewal clauses with no opt-out window
- Data sharing without explicit consent requirements
- Any clause with "irrevocable", "unconditional", or "sole discretion"

STANDARD BOILERPLATE — almost always approve these:
- Governing law / jurisdiction (unless heavily one-sided)
- Entire agreement / merger clause
- Severability, Counterparts, Notices
- Amendment procedure requiring written consent
- Force majeure, Headings

CONSISTENCY RULE:
Review your recent decisions before acting. Be consistent — if you flagged a
similar clause earlier, flag this one too.

Always respond ONLY in valid JSON. No text outside the JSON block."""

# ── Build User Prompt ─────────────────────────────────────────────────────────
def build_prompt(
    clause_text: str,
    task_id: str,
    clauses_reviewed: int,
    total_clauses: int,
    flags_raised: list,
    recent_history: list,
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

    boilerplate_hint = ", ".join(STANDARD_BOILERPLATE)

    return f"""CONTRACT TYPE : {contract_type}
PROGRESS      : Clause {clauses_reviewed + 1} of {total_clauses}
FLAGGED SO FAR: {', '.join(flags_raised) if flags_raised else 'None'}

YOUR LAST 3 DECISIONS:
{history_str}

STANDARD BOILERPLATE (approve unless clearly one-sided):
{boilerplate_hint}

CLAUSE TO REVIEW:
\"\"\"{clause_text}\"\"\"

REVIEW STEPS:
1. Identify clause type (liability, IP, indemnity, payment, termination, boilerplate, etc.)
2. Check for RISK SIGNALS from your instructions
3. Check if it is standard boilerplate — if so, lean toward approve
4. Be consistent with your recent decisions above
5. Choose the single best action: approve / flag / redline / escalate
6. Write a concise one-sentence reason
7. If redline, rewrite the clause to be safer

Respond ONLY in this exact JSON — nothing outside the braces:
{{
  "action": "approve|flag|redline|escalate",
  "reason": "one sentence explaining your decision",
  "suggested_edit": "rewritten clause text if redline, otherwise null"
}}"""

# ── FIX 1: High-risk keyword override ────────────────────────────────────────
def apply_risk_override(action: str, clause_text: str) -> str:
    """
    If the LLM tries to approve a clause containing high-risk keywords,
    override to flag. Prevents costly false negatives.
    """
    if action == "approve":
        text_lower = clause_text.lower()
        for keyword in HIGH_RISK_KEYWORDS:
            if keyword in text_lower:
                return "flag"
    return action

# ── Memory Helper ─────────────────────────────────────────────────────────────
def get_memory_mb() -> float:
    return psutil.Process().memory_info().rss / (1024 * 1024)

# ── Safe LLM Call with Retry ──────────────────────────────────────────────────
def call_llm(client: OpenAI, prompt: str, task_id: str, retry: bool = True) -> dict:
    # FIX 2: Task-specific token budget
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

        # Extract JSON even if model adds surrounding text
        start = cleaned.find("{")
        end   = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]

        return json.loads(cleaned)

    except json.JSONDecodeError:
        if retry:
            strict_prompt = (
                prompt
                + "\n\nWARNING: Your last response was not valid JSON. "
                "Reply ONLY with the JSON object. No preamble, no markdown, no explanation."
            )
            return call_llm(client, strict_prompt, task_id, retry=False)
        return {
            "action": "flag",
            "reason": "JSON parse error — defaulting to flag for safety",
            "suggested_edit": None,
        }

    except Exception as e:
        return {
            "action": "flag",
            "reason": f"API error — defaulting to flag ({type(e).__name__})",
            "suggested_edit": None,
        }

# ── Run Single Task ───────────────────────────────────────────────────────────
def run_task(env: LegalContractEnv, task_id: str, client: OpenAI) -> tuple:
    state      = env.reset(task_id)
    rewards    = []
    history    = []
    task_start = time.time()

    log_start(task=task_id, env="legal_evaluation", model=MODEL_NAME)

    while not state.done:

        # Guard: time limit
        if time.time() - task_start > MAX_TASK_SECONDS:
            log_step(
                step=state.clauses_reviewed,
                action="approve",
                reward=0.0,
                done=True,
                error="timeout",
            )
            break

        # Guard: memory limit
        if get_memory_mb() > MAX_MEMORY_MB:
            log_step(
                step=state.clauses_reviewed,
                action="approve",
                reward=0.0,
                done=True,
                error="memory_limit",
            )
            break

        # Extract clause safely (handles dict and object)
        if isinstance(state.current_clause, dict):
            clause_text = state.current_clause.get("text", "")
            clause_id   = state.current_clause.get("id", f"clause_{state.clauses_reviewed}")
        elif state.current_clause:
            clause_text = state.current_clause.text
            clause_id   = state.current_clause.id
        else:
            clause_text = ""
            clause_id   = f"clause_{state.clauses_reviewed}"

        # Build context-rich prompt (FIX 3 baked in)
        prompt = build_prompt(
            clause_text      = clause_text,
            task_id          = task_id,
            clauses_reviewed = state.clauses_reviewed,
            total_clauses    = state.total_clauses,
            flags_raised     = state.flags_raised,
            recent_history   = history,
        )

        # Call LLM with task-aware token budget (FIX 2)
        data           = call_llm(client, prompt, task_id)
        action_choice  = data.get("action", "flag").lower().strip()
        reason         = data.get("reason", "no reason provided")
        suggested_edit = data.get("suggested_edit", None)

        # Enforce allowed actions
        if action_choice not in ALLOWED_ACTIONS:
            action_choice = "flag"

        # FIX 1: Override approve on high-risk keywords
        action_choice = apply_risk_override(action_choice, clause_text)

        # Step environment
        action              = ActionParams(action=action_choice)
        state, reward, done = env.step(action)
        rewards.append(reward)

        # Track history for next prompt's context
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
            error  = None,
        )

    # Final scoring via grader
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
        score, steps = run_task(env, task, client)
        all_scores.append(score)

if __name__ == "__main__":
    main()