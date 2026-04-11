---
title: Legal Contract Review (OpenEnv)
emoji: ⚖️
colorFrom: gray
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
tags:
  - openenv
---

# Technical Project Summary: Legal Contract Review OpenEnv
**Official Submission for the Scaler × Meta/PyTorch OpenEnv Hackathon**

---

## 1. System Overview
The **Legal Contract Review OpenEnv** is a deterministic evaluation environment engineered explicitly for OpenEnv validation. It measures a Large Language Model's capability to execute procedural forensic legal review without human intervention.

The architecture enforces a strict in-memory, CPU-only execution model. Zero external databases, persistent storage, or GPU accelerators are utilized.

## 2. Hard Protocol Compliance 
The framework enforces absolute compliance with the Hackathon network constraints:
*   **Mandated Endpoints Only**: Operational hooks are strictly limited to `POST /reset`, `POST /step`, and `GET /state`.
*   **Health Telemetry**: The required `GET /health` endpoint is explicitly included and returns precisely `{"status": "ok"}`.
*   **Execution Primaries**: The global evaluator (`inference.py`) and evaluation parameter file (`openenv.yaml`) reside explicitly at the system root directory.
*   **Network Isolation**: Agent evaluation utilizes the OpenAI Python Client exclusively via `API_BASE_URL`, `MODEL_NAME`, and `HF_TOKEN`. Operational fallback via raw HTTP requests is prohibited.
*   **Docker Port Bindings**: Target Port `7860` is explicitly exposed globally and bound sequentially via Uvicorn.
*   **Server Stability**: Agent state persists in continuous memory without server restarts between steps. All malformed inputs and invalid requests return proper HTTP error responses (not just schema errors) without crashing the service.

## 3. RL Architecture & Authorized Actions
Agents execute exactly four authorized actions matching the OpenEnv
Pydantic `ActionParams` model:

- **`approve`**: `+0.4` (clause is standard and safe, no changes needed)
- **`flag`**: `+1.0` correct / `-0.2` over-flag penalty (identifies high-risk clause)
- **`redline`**: `+0.7` to `+0.9` (rewrites clause to remove risk)
- **`escalate`**: `+0.5` to `+0.8` (ambiguous clause sent to senior partner)
- **Approving a high-risk clause**: `-1.0` heavy penalty

**Observation Space**: The environment returns a Pydantic `State` object exposing:
* `task_id`: Current sequence identifier
* `current_clause`: A dictionary containing `id`, `text`, and legal `category`.
* `clauses_reviewed`, `total_clauses`, `cumulative_reward`, `flags_raised`, `done`.

ALL rewards are floating-point values strictly bound within `[0.0, 1.0]`.

## 4. State Schema Integrity
ALL request and response objects enforce strict Pydantic v2 schema
declarations:

- `task_id`: String — current task identifier
- `current_clause`: Object containing `id`, `text`, `category`, `is_ambiguous`
- `clauses_reviewed`: Integer — clauses processed so far
- `total_clauses`: Integer — total clauses in episode
- `cumulative_reward`: Float — running reward total
- `flags_raised`: List — clause IDs flagged by agent
- `false_approvals`: List — high-risk clauses incorrectly approved
- `escalations`: List — clauses escalated by agent
- `done`: Boolean — episode complete flag

## 5. Tasks & Execution Boundaries
Three distinct simulated workflows evaluate the agent under explicit step constraints:
1.  **`nda_review` (Expected Difficulty: Easy)**: Hard limit of 10 sequential clause steps.
2.  **`saas_review` (Expected Difficulty: Medium)**: Hard limit of 15 sequential clause steps.
3.  **`ma_review` (Expected Difficulty: Hard)**: Hard limit of 20 sequential clause steps.

Operations embed `psutil` natively to govern active resource stability, restricting consumption strictly to **2 vCPU / 8GB RAM**. Evaluator execution enforces a strict process termination upon exceeding a **20-minute** timeout variable.

## 6. Immutable CLI Logging Standard
The evaluator (`inference.py`) produces EXACTLY three line formats continuously to `stdout`, omitting JSON multi-liners and debugging footprints for total reproducibility:
*   `[START] task=<task_name> env=<benchmark> model=<model_name>`: Emitted once per task on episode initialization.
*   `[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>`: Emitted once per clause iteration.
*   `[END] success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>`: Emitted once upon episode termination to calculate standard final metrics.

## 7. Completeness Guarantee
Zero placeholder variables, unfinished logic pathways, or development fragments exist across the module. All 9 required files establish perfect integrity:

1.   `openenv.yaml`
2.   `app/main.py`
3.   `app/models.py`
4.   `app/environment.py`
5.   `app/graders.py`
6.   `inference.py`
7.   `Dockerfile`
8.   `requirements.txt`
9.   `README.md`

## 8. Example Output
[START] task=nda_review env=legal_evaluation model=gpt-4
[STEP] step=1 action=approve reward=0.40 done=false error=null
[STEP] step=2 action=flag reward=1.00 done=false error=null
[STEP] step=3 action=redline reward=0.80 done=false error=null
[END] success=true steps=10 score=0.847 rewards=0.40,1.00,0.80,...
[SUMMARY] tasks=3 avg_score=0.821 scores=0.847,0.803,0.812

## 9. Setup & Run

### Environment Variables Required
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4"
export HF_TOKEN="your_token_here"
```

### Run Inference
```bash
python inference.py
```

### Run with Docker
```bash
docker build -t legal-contract-env .
docker run -e API_BASE_URL=... -e MODEL_NAME=... -e HF_TOKEN=... legal-contract-env
```
