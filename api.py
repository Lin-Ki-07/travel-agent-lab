from dataclasses import asdict
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from agents.conversation_agent import ConversationAgent
from agents.edit_draft_agent import EditDraftAgent
from agents.travel_tools import create_web_travel_agent
from core.chat_contract import ChatRequest, EditDraft
from core.chat_service import needs_travel_tools, reply_to_chat, reply_with_travel_tools
from core.edit_draft_service import confirm_edit_draft, generate_edit_draft
from core.config import LLMConfig
from core.exceptions import LLMError
from core.trip_edit import edit_day
from core.trip_routes import refresh_edited_day_routes, complete_missing_routes
from core.llm_client import OpenAICompatibleClient
from core.trip_models import Itinerary
from core.trip_service import plan_trip
from core.trip_parser import parse_trip_text
from core.trip_store import (
    itinerary_fingerprint, update_itinerary_if_unchanged,
    delete_itinerary, list_saved_plans, load_itinerary, load_preferences, save_itinerary,
    save_preferences, update_itinerary,
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
        effective_request = dict(raw_request)
        if not effective_request.get("preferences", "").strip():
            effective_request["preferences"] = ",".join(load_preferences())
        itinerary = plan_trip(create_llm(), effective_request)
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


@app.post("/api/chat")
def chat(raw_request: dict) -> dict:
    """回答普通问题；编辑草案和保存留待后续步骤。"""
    try:
        request = ChatRequest.model_validate(raw_request)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc

    itinerary = None
    if request.plan_id is not None:
        itinerary = load_itinerary(request.plan_id) or generated_plans.get(request.plan_id)
        if itinerary is None:
            raise HTTPException(status_code=404, detail="行程不存在")

    try:
        llm = create_llm()
        if needs_travel_tools(request.text):
            response = reply_with_travel_tools(create_web_travel_agent(llm), request, itinerary)
        else:
            response = reply_to_chat(ConversationAgent(llm), request, itinerary)
    except (LLMError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@app.post("/api/plans/{plan_id}/edit-draft")
def create_edit_draft(plan_id: str, raw: dict) -> dict:
    """生成替换预览；不保存行程。"""
    itinerary = load_itinerary(plan_id) or generated_plans.get(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    try:
        day_number = raw["day_number"]
        activity_index = raw["activity_index"]
        original_place_id = raw["original_place_id"]
        candidate_place_id = raw["candidate_place_id"]
        if type(day_number) is not int or type(activity_index) is not int:
            raise ValueError("目标序号必须是整数")
        if not all(isinstance(item, str) and item.strip() for item in (original_place_id, candidate_place_id)):
            raise ValueError("地点 ID 不能为空")
        response = generate_edit_draft(
            lambda: EditDraftAgent(create_llm()), itinerary, plan_id, day_number,
            activity_index, original_place_id, candidate_place_id,
        )
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (LLMError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@app.post("/api/plans/{plan_id}/edit-draft/confirm")
def confirm_plan_edit_draft(plan_id: str, raw: dict) -> dict:
    """确认草案并原子更新已保存行程。"""
    itinerary = load_itinerary(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="已保存行程不存在")
    try:
        draft = EditDraft.model_validate(raw)
        return confirm_edit_draft(itinerary, plan_id, draft)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/preferences")
def get_preferences() -> dict:
    return {"preferences": load_preferences()}


@app.put("/api/preferences")
def put_preferences(raw: dict) -> dict:
    preferences = raw.get("preferences")
    if not isinstance(preferences, list) or any(
        not isinstance(item, str) for item in preferences
    ):
        raise HTTPException(status_code=422, detail="preferences 必须是字符串列表")
    try:
        return {"preferences": save_preferences(preferences)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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


@app.delete("/api/plans/{plan_id}")
def delete_plan(plan_id: str) -> dict:
    deleted_saved = delete_itinerary(plan_id)
    deleted_generated = generated_plans.pop(plan_id, None) is not None
    if not deleted_saved and not deleted_generated:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"plan_id": plan_id, "deleted": True}


@app.put("/api/plans/{plan_id}/days/{day_number}")
def update_plan_day(plan_id: str, day_number: int, raw: dict) -> dict:
    itinerary = load_itinerary(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="已保存行程不存在")

    try:
        edited = edit_day(itinerary, day_number, raw)
        edited = refresh_edited_day_routes(itinerary, edited, day_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not update_itinerary(plan_id, edited):
        raise HTTPException(status_code=404, detail="已保存行程不存在")

    return {
        "plan_id": plan_id,
        "itinerary": jsonable_encoder(asdict(edited)),
        "map_days": build_map_days(edited),
    }


@app.post("/api/plans/{plan_id}/routes/complete")
def complete_plan_routes(plan_id: str) -> dict:
    itinerary = load_itinerary(plan_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="已保存行程不存在")
    fingerprint = itinerary_fingerprint(itinerary)
    updated = complete_missing_routes(itinerary)
    if not update_itinerary_if_unchanged(plan_id, updated, fingerprint):
        raise HTTPException(status_code=409, detail="行程已变化，请重新打开后补全交通")
    return {"plan_id": plan_id, "itinerary": jsonable_encoder(asdict(updated)),
            "map_days": build_map_days(updated)}
