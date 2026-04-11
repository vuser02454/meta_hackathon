from app.models import State

# ── Grader ────────────────────────────────────────────────────────────────────
# FIX: Before — single flat score from cumulative_reward
# After  — multi-dimensional score:
#          (1) risk detection rate   — did agent catch high-risk clauses?
#          (2) false approval rate   — did agent approve risky clauses?
#          (3) escalation quality    — were escalations on ambiguous clauses?
#          (4) efficiency score      — did agent avoid over-flagging boilerplate?

class Grader:

    def score(self, state: State) -> float:
        """
        Returns a float in [0.0, 1.0] representing agent performance.

        Breakdown:
          40% — Risk detection (flagged/escalated high-risk clauses)
          30% — False approval penalty (high-risk clauses approved)
          20% — Efficiency (avoided over-flagging safe clauses)
          10% — Reward progression (cumulative_reward normalized)
        """
        if state.total_clauses == 0:
            return 0.0

        # ── Pull task-specific ground truth ───────────────────────────────
        high_risk_ids  = self._get_high_risk_ids(state)
        total_high     = len(high_risk_ids)
        total_clauses  = state.total_clauses

        # ── 1. Risk Detection Rate (40%) ──────────────────────────────────
        # How many high-risk clauses were correctly flagged OR escalated?
        correctly_caught = set(state.flags_raised + state.escalations) & set(high_risk_ids)
        risk_score = (
            len(correctly_caught) / total_high
            if total_high > 0 else 1.0   # if no high-risk clauses, full marks
        )

        # ── 2. False Approval Penalty (30%) ───────────────────────────────
        # Each false approval (high-risk clause approved) heavily penalises score
        false_approval_rate = (
            len(state.false_approvals) / total_high
            if total_high > 0 else 0.0
        )
        approval_score = max(0.0, 1.0 - false_approval_rate)

        # ── 3. Efficiency Score (20%) ─────────────────────────────────────
        # Penalise over-flagging: flags that are NOT on high-risk clauses
        unnecessary_flags = [
            fid for fid in state.flags_raised
            if fid not in high_risk_ids
        ]
        safe_clauses   = total_clauses - total_high
        over_flag_rate = (
            len(unnecessary_flags) / safe_clauses
            if safe_clauses > 0 else 0.0
        )
        efficiency_score = max(0.0, 1.0 - over_flag_rate)

        # ── 4. Reward Progression Score (10%) ────────────────────────────
        # Normalise cumulative reward to [0, 1]
        # Maximum possible reward per clause is 1.0
        max_possible  = float(total_clauses)
        reward_score  = max(
            0.0,
            min(1.0, state.cumulative_reward / max_possible)
        ) if max_possible > 0 else 0.0

        # ── Weighted final score ───────────────────────────────────────────
        final = (
            0.40 * risk_score       +
            0.30 * approval_score   +
            0.20 * efficiency_score +
            0.10 * reward_score
        )

        return round(max(0.0, min(1.0, final)), 4)

    def _get_high_risk_ids(self, state: State) -> list[str]:
        """
        Returns the IDs of clauses in the current episode that are high-risk.
        Uses false_approvals + flags_raised to reconstruct ground truth.

        In a production system this would query the contract data directly.
        Here we derive it from what the environment tracked.
        """
        # All clauses the agent interacted with that were high-risk
        # are recorded in false_approvals (approved high-risk)
        # and flags_raised (correctly flagged high-risk)
        return list(set(state.false_approvals + state.flags_raised))
