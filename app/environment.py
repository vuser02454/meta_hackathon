import random
from typing import Optional
from app.models import Clause, ActionParams, State


# ── Reward Table ──────────────────────────────────────────────────────────────
# FIX 1: Reward clamping now happens AFTER all bonuses (not before)
# FIX 2: Reason bonus only fires when reason is meaningful (not default fallback)
REWARD_TABLE = {
    ("approve",  "low"):    +0.4,
    ("approve",  "medium"): -0.3,
    ("approve",  "high"):   -1.0,   # critical failure
    ("flag",     "low"):    -0.2,   # over-flagging boilerplate
    ("flag",     "medium"): +0.6,
    ("flag",     "high"):   +1.0,   # perfect catch
    ("redline",  "low"):    -0.1,
    ("redline",  "medium"): +0.7,
    ("redline",  "high"):   +0.9,
    ("escalate", "low"):    -0.2,
    ("escalate", "medium"): +0.5,
    ("escalate", "high"):   +0.8,
}

FALLBACK_REASONS = {
    "no reason provided",
    "json parse error fallback",
    "",
}


# ── Clause Pools ──────────────────────────────────────────────────────────────
NDA_CLAUSE_POOL = [
    Clause(id="nda_01", text="Both parties agree to keep all shared information strictly confidential for a period of 3 years from the date of disclosure.", category="confidentiality", risk_level="low"),
    Clause(id="nda_02", text="Either party may be held liable for unlimited damages in the event of any breach of this agreement.", category="liability", risk_level="high"),
    Clause(id="nda_03", text="This agreement shall be governed by the laws of the State of Delaware.", category="boilerplate", risk_level="low"),
    Clause(id="nda_04", text="The receiving party shall have the irrevocable right to sublicense any confidential information to third parties without prior consent.", category="IP", risk_level="high"),
    Clause(id="nda_05", text="Either party may terminate this agreement at any time without notice and without liability.", category="termination", risk_level="high"),
    Clause(id="nda_06", text="Any amendments to this agreement must be made in writing and signed by both parties.", category="boilerplate", risk_level="low"),
    Clause(id="nda_07", text="Confidential information shall not include information that becomes publicly available through no fault of the receiving party.", category="confidentiality", risk_level="low"),
    Clause(id="nda_08", text="The disclosing party waives all rights to seek injunctive relief in the event of a breach.", category="liability", risk_level="high"),
    Clause(id="nda_09", text="This agreement constitutes the entire understanding between the parties.", category="boilerplate", risk_level="low"),
    Clause(id="nda_10", text="The receiving party may use confidential information for any purpose at its sole discretion.", category="IP", risk_level="high"),
    Clause(id="nda_11", text="Notices under this agreement shall be sent via email to the addresses provided.", category="boilerplate", risk_level="low"),
    Clause(id="nda_12", text="The indemnifying party shall defend and hold harmless the other party from any and all claims arising from this agreement with no cap on liability.", category="indemnity", risk_level="high"),
    # Extra low-risk clauses to ensure we always have enough after planting high-risk ones
    Clause(id="nda_13", text="The parties agree that this agreement may be executed in counterparts.", category="boilerplate", risk_level="low"),
    Clause(id="nda_14", text="Neither party shall assign its rights under this agreement without prior written consent.", category="boilerplate", risk_level="low"),
]

SAAS_CLAUSE_POOL = [
    Clause(id="saas_01", text="Customer shall pay all fees within 30 days of invoice date.", category="payment", risk_level="low"),
    Clause(id="saas_02", text="Vendor retains all intellectual property rights in the software and any derivatives thereof.", category="IP", risk_level="medium"),
    Clause(id="saas_03", text="Vendor may share customer data with any third party at its sole discretion without customer consent.", category="confidentiality", risk_level="high"),
    Clause(id="saas_04", text="The SLA guarantees 99.9% uptime. Failure to meet this results in a 10% service credit.", category="payment", risk_level="low"),
    Clause(id="saas_05", text="Vendor may unilaterally modify pricing at any time without prior notice to the customer.", category="payment", risk_level="high"),
    Clause(id="saas_06", text="This agreement auto-renews annually unless either party provides 90 days written notice of non-renewal.", category="termination", risk_level="medium"),
    Clause(id="saas_07", text="Customer grants vendor an unconditional, perpetual, irrevocable license to use all customer data for any purpose.", category="IP", risk_level="high"),
    Clause(id="saas_08", text="Either party may terminate for cause upon 30 days written notice.", category="termination", risk_level="low"),
    Clause(id="saas_09", text="Vendor's total liability shall not exceed fees paid in the prior 3 months.", category="liability", risk_level="medium"),
    Clause(id="saas_10", text="Customer is responsible for all taxes and duties applicable to the services.", category="payment", risk_level="low"),
    Clause(id="saas_11", text="Vendor may suspend services immediately without notice for any perceived violation.", category="termination", risk_level="high"),
    Clause(id="saas_12", text="All disputes shall be resolved by binding arbitration under AAA rules.", category="boilerplate", risk_level="low"),
    Clause(id="saas_13", text="Customer data is processed in accordance with GDPR and applicable privacy laws.", category="confidentiality", risk_level="low"),
    Clause(id="saas_14", text="Vendor shall not be liable for any indirect, incidental, or consequential damages.", category="liability", risk_level="medium"),
    Clause(id="saas_15", text="Customer waives all rights to class action lawsuits against the vendor.", category="liability", risk_level="high"),
    Clause(id="saas_16", text="Force majeure events shall excuse performance for a maximum of 90 days.", category="boilerplate", risk_level="low"),
    Clause(id="saas_17", text="Any IP created by vendor using customer data is owned exclusively by vendor.", category="IP", risk_level="high"),
    Clause(id="saas_18", text="This agreement is governed by the laws of California.", category="boilerplate", risk_level="low"),
    Clause(id="saas_19", text="Either party may request an audit of the other's data handling practices with 30 days notice.", category="confidentiality", risk_level="low"),
    Clause(id="saas_20", text="Vendor shall provide customer with 30 days notice before any material change to the service.", category="boilerplate", risk_level="low"),
]

MA_CLAUSE_POOL = [
    Clause(id="ma_01", text="Seller represents that there are no undisclosed liabilities, contingent or otherwise, as of the closing date.", category="indemnity", risk_level="medium", is_ambiguous=True),
    Clause(id="ma_02", text="Buyer assumes all liabilities of the target company, whether known or unknown, without limitation.", category="liability", risk_level="high"),
    Clause(id="ma_03", text="The purchase price is subject to a working capital adjustment calculated 90 days post-closing.", category="payment", risk_level="medium"),
    Clause(id="ma_04", text="All intellectual property created by employees of the target prior to closing is irrevocably transferred to buyer.", category="IP", risk_level="high"),
    Clause(id="ma_05", text="Seller shall indemnify buyer for any claims arising from pre-closing operations with no cap on indemnification.", category="indemnity", risk_level="high"),
    Clause(id="ma_06", text="Closing is conditioned upon regulatory approval and satisfaction of all conditions precedent.", category="boilerplate", risk_level="low"),
    Clause(id="ma_07", text="Non-compete obligations shall bind seller for a period of 5 years across all global markets.", category="termination", risk_level="high", is_ambiguous=True),
    Clause(id="ma_08", text="Representations and warranties survive closing for a period of 18 months.", category="indemnity", risk_level="medium"),
    Clause(id="ma_09", text="Any material adverse change shall be determined at buyer's sole discretion.", category="liability", risk_level="high", is_ambiguous=True),
    Clause(id="ma_10", text="Target's existing customer contracts transfer automatically upon closing without consent.", category="IP", risk_level="high"),
    Clause(id="ma_11", text="This agreement is governed by Delaware law and disputes resolved in Delaware courts.", category="boilerplate", risk_level="low"),
    Clause(id="ma_12", text="Escrow of 15% of purchase price held for 12 months to cover indemnification claims.", category="payment", risk_level="medium"),
    Clause(id="ma_13", text="Seller waives all rights to any earn-out payments if buyer determines performance metrics were not met.", category="payment", risk_level="high", is_ambiguous=True),
    Clause(id="ma_14", text="Buyer may unilaterally assign this agreement to any affiliate without seller consent.", category="IP", risk_level="high"),
    Clause(id="ma_15", text="All key employees must sign retention agreements as a condition of closing.", category="boilerplate", risk_level="low"),
    Clause(id="ma_16", text="Seller is responsible for all pre-closing tax liabilities with no limitation on amount.", category="liability", risk_level="high"),
    Clause(id="ma_17", text="Confidentiality obligations survive termination of this agreement for a period of 3 years.", category="confidentiality", risk_level="low"),
    Clause(id="ma_18", text="The definition of confidential information includes all non-public data, at buyer's sole determination.", category="confidentiality", risk_level="high", is_ambiguous=True),
    Clause(id="ma_19", text="Dispute resolution via arbitration under ICC rules in New York.", category="boilerplate", risk_level="low"),
    Clause(id="ma_20", text="Seller unconditionally guarantees all representations made about target's revenue projections.", category="indemnity", risk_level="high"),
    Clause(id="ma_21", text="Buyer may terminate this agreement for any reason within 10 business days of signing.", category="termination", risk_level="medium"),
    Clause(id="ma_22", text="All outstanding litigation against the target shall be disclosed prior to closing.", category="indemnity", risk_level="medium"),
    # FIX 4: Extra clauses added so ma_review has genuine randomization (was only 22 for n=20)
    Clause(id="ma_23", text="Seller warrants that all financial statements provided are accurate and complete in all material respects.", category="indemnity", risk_level="medium"),
    Clause(id="ma_24", text="Buyer assumes sole responsibility for integration costs post-closing with no recourse to seller.", category="liability", risk_level="high"),
    Clause(id="ma_25", text="All environmental liabilities of the target company transfer to buyer unconditionally.", category="liability", risk_level="high"),
    Clause(id="ma_26", text="This agreement shall be binding upon and inure to the benefit of the parties and their successors.", category="boilerplate", risk_level="low"),
    Clause(id="ma_27", text="Seller may not solicit any employees of the target company for a period of 2 years post-closing.", category="termination", risk_level="low"),
    Clause(id="ma_28", text="The purchase price shall be adjusted downward if net revenue falls below projections by more than 10%.", category="payment", risk_level="medium", is_ambiguous=True),
]


# ── Task Config ────────────────────────────────────────────────────────────────
TASK_CONFIG = {
    "nda_review":  {"pool": NDA_CLAUSE_POOL,  "n_clauses": 10},
    "saas_review": {"pool": SAAS_CLAUSE_POOL, "n_clauses": 15},
    "ma_review":   {"pool": MA_CLAUSE_POOL,   "n_clauses": 20},
}


class LegalContractEnv:
    """
    OpenEnv-compliant environment for legal contract review.

    FIXES APPLIED:
    1. Reward clamping now happens AFTER bonuses — no reward > 1.0
    2. Reason bonus only fires on meaningful reasons — not fallback strings
    3. flags_raised tracks ALL correct flags (high + medium) separately
    4. MA pool expanded to 28 clauses — genuine randomization for hardest task
    5. Clause sampling bug fixed — guaranteed to always produce exactly n clauses
    6. all_high_risk_ids stored in state — grader has true ground truth
    """

    def __init__(self):
        self._state:   Optional[State] = None
        self._clauses: list[Clause]    = []
        self._cursor:  int             = 0

    # ── reset ─────────────────────────────────────────────────────────────────
    def reset(self, task_id: str) -> State:
        if task_id not in TASK_CONFIG:
            raise ValueError(
                f"Unknown task_id: '{task_id}'. "
                f"Must be one of {list(TASK_CONFIG.keys())}"
            )

        config = TASK_CONFIG[task_id]
        pool   = config["pool"]
        n      = config["n_clauses"]

        # FIX 5: Guaranteed clause count — always produce exactly n clauses
        # Step 1: separate high and non-high clauses
        high_risk_pool = [c for c in pool if c.risk_level == "high"]
        other_pool     = [c for c in pool if c.risk_level != "high"]

        # Step 2: plant exactly 3 high-risk clauses (or all if fewer exist)
        n_plant  = min(3, len(high_risk_pool))
        planted  = random.sample(high_risk_pool, n_plant)

        # Step 3: fill remaining slots with non-high clauses
        n_fill   = n - n_plant
        fillers  = random.sample(other_pool, min(n_fill, len(other_pool)))

        # Step 4: if still short (edge case), top up with remaining high-risk
        combined = planted + fillers
        if len(combined) < n:
            extras = [c for c in high_risk_pool if c not in planted]
            combined += extras[: n - len(combined)]

        random.shuffle(combined)
        self._clauses = combined[:n]
        self._cursor  = 0

        # FIX 6: Store ground truth high-risk IDs in state for grader
        all_high_ids = [c.id for c in self._clauses if c.risk_level == "high"]

        self._state = State(
            task_id           = task_id,
            current_clause    = self._clauses[0] if self._clauses else None,
            clauses_reviewed  = 0,
            total_clauses     = len(self._clauses),
            cumulative_reward = 0.0,
            flags_raised      = [],
            escalations       = [],
            false_approvals   = [],
            medium_flags      = [],
            all_high_risk_ids = all_high_ids,
            done              = False,
        )
        return self._state

    # ── step ──────────────────────────────────────────────────────────────────
    def step(self, action: ActionParams) -> tuple[State, float, bool]:
        if self._state is None or self._state.done:
            raise RuntimeError("Call reset() before step()")

        current = self._clauses[self._cursor]
        act     = action.action.lower().strip()

        # Base reward from table
        reward = REWARD_TABLE.get((act, current.risk_level), 0.0)

        # FIX 1 + 2: Bonuses calculated BEFORE clamp, only on meaningful reasons
        reason_text = (action.reason or "").lower().strip()
        if reason_text and reason_text not in FALLBACK_REASONS:
            reward += 0.05

        if act == "redline" and action.suggested_edit:
            reward += 0.1

        # Clamp AFTER all bonuses are applied
        reward = max(-1.0, min(1.0, reward))

        # FIX 3: Track flags separately for high and medium risk
        if act == "flag":
            if current.risk_level == "high":
                self._state.flags_raised.append(current.id)
            elif current.risk_level == "medium":
                self._state.medium_flags.append(current.id)

        if act == "escalate":
            self._state.escalations.append(current.id)

        if act == "approve" and current.risk_level == "high":
            self._state.false_approvals.append(current.id)

        # Advance
        self._cursor                  += 1
        self._state.clauses_reviewed  += 1
        self._state.cumulative_reward  = round(
            self._state.cumulative_reward + reward, 4
        )

        done               = self._cursor >= len(self._clauses)
        self._state.done   = done
        self._state.current_clause = (
            self._clauses[self._cursor] if not done else None
        )

        return self._state, reward, done

    # ── state ─────────────────────────────────────────────────────────────────
    def state(self) -> State:
        if self._state is None:
            raise RuntimeError("Call reset() first")
        return self._state
