# Legal Contract Review (OpenEnv)

## Description
This OpenEnv environment enables evaluating agents on reviewing legal contracts step-by-step. The agent must identify the risk level of each clause and take the appropriate action (approve, flag, redline, or escalate). 

## Action and Observation Space

| Space | Format | Description |
|-------|--------|-------------|
| **Observation** | JSON (`State` object) | Contains `contract_id`, `task_id`, `current_clause`, `step_number`, `total_clauses`, and `review_history`. The `current_clause` reveals the text and type but hides the `risk_level`. |
| **Action** | JSON (`Action` object) | Contains `action` (one of "flag", "redline", "approve", "escalate"), `clause_id`, `reason` (string), and `suggested_edit` (string, optional). |

## Setup and Run Instructions

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Inference (Agent Loop):**
   Set the required API variables and run the script:
   ```bash
   export API_BASE_URL="your-api-base"
   export MODEL_NAME="your-model-name"
   export HF_TOKEN="your-hf-token"
   python inference.py
   ```

3. **Run API Server (Docker):**
   Build and run the Docker image to mount the FastAPI interface on port 7860.
   ```bash
   docker build -t legal-env .
   docker run -p 7860:7860 legal-env
   ```
   Or natively:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 7860
   ```

## Example Scores Per Task

- Task 1 (Easy): `0.5` (Identified 1 out of 2 high-risk clauses)
- Task 2 (Medium): `0.85` (Reasonable weighted F1 on risk detection)
- Task 3 (Hard): `0.6` (Good risk coverage but partially incorrect escalations)

## Environment Variables Needed
To use `inference.py`, the following variables should be set:
- `API_BASE_URL`: Base URL for the OpenAI-compatible API
- `MODEL_NAME`: The model routing name
- `HF_TOKEN`: Hugging Face or provider token
