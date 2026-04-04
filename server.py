from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from environment.env import LegalContractEnv
from environment.models import Action, State, EpisodeResult

app = FastAPI(title="Legal Contract Review OpenEnv API")
env = LegalContractEnv()

class ResetRequest(BaseModel):
    task_id: str

@app.get("/")
async def root():
    return {"message": "Legal Contract Review OpenEnv API is running", "version": "1.0.0"}

@app.post("/reset", response_model=State)
async def reset(request: ResetRequest):
    try:
        return env.reset(request.task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
async def step(action: Action):
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
async def get_state():
    try:
        return env.state()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/grade")
async def grade():
    try:
        return {"score": env.grade()}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/episode_result", response_model=EpisodeResult)
async def get_episode_result():
    try:
        return env.episode_result()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
