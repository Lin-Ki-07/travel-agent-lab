from dataclasses import asdict
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder

from core.config import LLMConfig
from core.trip_edit import edit_day
from core.llm_client import OpenAICompatibleClient
from core.trip_models import Itinerary
from core.trip_service import plan_trip
from core.trip_parser import parse_trip_text
from core.trip_store import (
    list_saved_plans, load_itinerary, save_itinerary, update_itinerary,
)
from core.map_view import build_map_days

load_dotenv()

app = FastAPI(title="Travel Agent Lab", version="0.4.0")

@app.get("/")
def service_info() -> dict[str, str]:
    """提供本地后端入口说明，不调用模型或外部服务。"""
    return {
        "service": "Travel Agent Lab API",
        "message": "后端服务已启动，请在前端页面使用旅行规划功能。",
        "docs": "/docs",
        "frontend": "http://127.0.0.1:5173",
    }

generated_plans: dict[str, Itinerary] = {}

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
        "map_days": build_map_days(itinerary),
    }

@app.post("/api/plans/parse")
def parse_request(raw_request: dict[str, str]) -> dict:
    """把一句自然语言需求解析为表单字段；只解析，不保存，不生成行程。"""
    text = raw_request.get("text", "")
    try:
        return parse_trip_text(create_llm(), text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.get("/api/plans")
def get_saved_plans() -> dict:
    return {"plans": list_saved_plans()}

@app.post("/api/plans/{plan_id}/save")
def save_plan(plan_id: str) -> dict:
    itinerary = generated_plans.get(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="行程不存在")

    save_itinerary(plan_id, itinerary)
    return {"plan_id": plan_id, "saved": True}


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str) -> dict:
    itinerary = load_itinerary(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="行程不存在或尚未保存")

    return {
        "plan_id": plan_id,
        "itinerary": jsonable_encoder(asdict(itinerary)),
        "map_days": build_map_days(itinerary),
    }


@app.put("/api/plans/{plan_id}/days/{day_number}")
def update_plan_day(plan_id: str, day_number: int, raw: dict) -> dict:
    itinerary = load_itinerary(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="已保存行程不存在")

    try:
        edited = edit_day(itinerary, day_number, raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not update_itinerary(plan_id, edited):
        raise HTTPException(status_code=404, detail="已保存行程不存在")

    return {
        "plan_id": plan_id,
        "itinerary": jsonable_encoder(asdict(edited)),
        "map_days": build_map_days(edited),
    }
