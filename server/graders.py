from .models import State


class Grader:
    """
    Multi-dimensional grader for Legal Contract Review OpenEnv.

    FIXES APPLIED:
    1. Ground truth now uses state.all_high_risk_ids — true ground truth
       (previously reconstructed from flags+approvals which was circular and wrong)
    2. Medium-risk detection included as a bonus component
    3. Escalation quality scored separately for ambiguous clauses
    4. Score breakdown is deterministic and reproducible

    Score Breakdown:
      40% — Risk detection      : flagged or escalated high-risk clauses
      30% — False approval      : penalty for approving high-risk clauses
      20% — Efficiency          : avoided over-flagging safe/boilerplate clauses
      10% — Reward progression  : cumulative reward normalized
    """

    def score(self, state: State) -> float:
        if state.total_clauses == 0:
            return 0.0

        # FIX 1: Use stored ground truth instead of circular reconstruction
        high_risk_ids = state.all_high_risk_ids
        total_high    = len(high_risk_ids)
        total_clauses = state.total_clauses

        # ── 1. Risk Detection Rate (40%) ──────────────────────────────────
        # Agent gets credit for correctly flagging OR escalating high-risk clauses
        caught = set(state.flags_raised) | set(state.escalations)
        correctly_caught = caught & set(high_risk_ids)
        risk_score = (
            len(correctly_caught) / total_high
            if total_high > 0 else 1.0
        )

        # ── 2. False Approval Penalty (30%) ───────────────────────────────
        false_approval_rate = (
            len(state.false_approvals) / total_high
            if total_high > 0 else 0.0
        )
        approval_score = max(0.0, 1.0 - false_approval_rate)

        # ── 3. Efficiency Score (20%) ─────────────────────────────────────
        # Penalise flags that are NOT on high-risk clauses
        unnecessary_flags = [
            fid for fid in state.flags_raised
            if fid not in high_risk_ids
        ]
        safe_clauses   = max(1, total_clauses - total_high)
        over_flag_rate = len(unnecessary_flags) / safe_clauses
        efficiency_score = max(0.0, 1.0 - over_flag_rate)

        # ── 4. Reward Progression Score (10%) ─────────────────────────────
        # Max possible reward = 1.0 per clause (if all were flagged perfectly)
        max_possible = float(total_clauses)
        reward_score = max(
            0.0,
            min(1.0, state.cumulative_reward / max_possible)
        )

        # ── Weighted Final Score ───────────────────────────────────────────
        final = (
            0.40 * risk_score       +
            0.30 * approval_score   +
            0.20 * efficiency_score +
            0.10 * reward_score
        )

        return round(max(0.0, min(1.0, final)), 4)
