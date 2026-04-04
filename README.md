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
Agents execute exactly four authorized actions. All unapproved action strings are rejected natively.

ALL rewards are floating-point values. ALL rewards are strictly within `[0.0, 1.0]`. This includes both action rewards and final score. All numerical outputs are floating-point values.

*   **`flag`**: `0.2`
*   **`escalate`**: `0.25`
*   **`redline`**: `0.3`
*   **`synthesize`**: `0.4`

## 4. State Schema Integrity
ALL request and response objects enforce strict Pydantic v2 schema declarations:
*   `task_id`: String
*   `current_clause`: Complete object containing precisely `id`, `text`, and `category`.
*   `clauses_reviewed`: Integer
*   `total_clauses`: Integer
*   `cumulative_reward`: Float
*   `flags_raised`: List
*   `done`: Boolean

## 5. Execution Boundary Limits
Computational limits enforce hard algorithmic cutoffs:
1.  **`nda_review`**: Hard limit of 10 sequence steps.
2.  **`saas_review`**: Hard limit of 15 sequence steps.
3.  **`ma_review`**: Hard limit of 20 sequence steps.

Operations embed `psutil` natively to govern active resource stability, restricting consumption strictly to **2 vCPU / 8GB RAM**. Evaluator execution enforces a strict process termination upon exceeding a **20-minute** timeout variable.

## 6. Immutable Logging Standard
Logs EXACTLY match `[START]`, `[STEP]`, `[END]`. No additional or missing fields.
*   `[START]`: Emitted once per task on episode initialization.
*   `[STEP]`: Emitted once per clause iteration during the episode.
*   `[END]`: Emitted once per task upon episode termination.

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
