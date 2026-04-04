from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.environment import LegalContractEnv
from app.models import State, ActionParams

app = FastAPI(title="Legal Contract Review Hackathon Env")
env = LegalContractEnv()

class ResetRequest(BaseModel):
    task_id: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset", response_model=State)
def reset(request: ResetRequest):
    try:
        return env.reset(request.task_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
def step(action: ActionParams):
    try:
        state, reward, done = env.step(action)
        return {
            "state": state,
            "reward": reward,
            "done": done
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state", response_model=State)
def state():
    if env.state is None:
        raise HTTPException(status_code=400, detail="Environment not reset")
    return env.state
