from dataclasses import asdict
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder

from core.config import LLMConfig
from core.llm_client import OpenAICompatibleClient
from core.trip_models import Itinerary
from core.trip_service import plan_trip

load_dotenv()

app = FastAPI(title="Travel Agent Lab", version="0.4.0")

generated_plans: dict[str, Itinerary] = {}
saved_plan_ids: set[str] = set()

def create_llm() -> OpenAICompatibleClient:
    config = LLMConfig.from_env()
    return OpenAICompatibleClient(
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout,
        temperature=config.temperature,
    )

@app.post("/api/plans")
def create_plan(raw_request: dict[str, str]) -> dict:
    try:
        itinerary = plan_trip(create_llm(), raw_request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    plan_id = uuid4().hex
    generated_plans[plan_id] = itinerary
    return {
        "plan_id": plan_id,
        "itinerary": jsonable_encoder(asdict(itinerary)),
    }

@app.post("/api/plans/{plan_id}/save")
def save_plan(plan_id: str) -> dict:
    if plan_id not in generated_plans:
        raise HTTPException(status_code=404, detail="行程不存在")

    saved_plan_ids.add(plan_id)
    return {"plan_id": plan_id, "saved": True}


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str) -> dict:
    if plan_id not in saved_plan_ids:
        raise HTTPException(status_code=404, detail="行程不存在或尚未保存")

    itinerary = generated_plans[plan_id]
    return {
        "plan_id": plan_id,
        "itinerary": jsonable_encoder(asdict(itinerary)),
    }