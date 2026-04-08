from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from server.environment import LegalContractEnv
from server.models import State, ActionParams

app = FastAPI(title="Legal Contract Review Hackathon Env")
env = LegalContractEnv()

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))

from typing import Optional

class ResetRequest(BaseModel):
    task_id: str = "nda_review"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset", response_model=State)
def reset(request: Optional[ResetRequest] = None):
    task_id = request.task_id if request else "nda_review"
    try:
        return env.reset(task_id)
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

def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)
