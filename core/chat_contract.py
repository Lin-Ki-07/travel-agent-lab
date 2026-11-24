"""v0.7.0 对话响应的数据契约；本模块不调用模型或写入行程。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ChatMessage(ContractModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(ContractModel):
    text: str = Field(min_length=1)
    plan_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class AnswerResponse(ContractModel):
    kind: Literal["answer"] = "answer"
    message: str = Field(min_length=1)


class ClarifyResponse(ContractModel):
    kind: Literal["clarify"] = "clarify"
    message: str = Field(min_length=1)


class ActivityTarget(ContractModel):
    day_number: int = Field(ge=1)
    activity_index: int = Field(ge=0)
    place_id: str = Field(min_length=1)


class EditTargetResponse(ContractModel):
    kind: Literal["edit_target"] = "edit_target"
    message: str = Field(min_length=1)
    target: ActivityTarget


class DraftActivity(ContractModel):
    place_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")


class DraftTransport(ContractModel):
    from_place_id: str = Field(min_length=1)
    to_place_id: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    estimated_minutes: int | None = Field(default=None, ge=0)


class EditDraft(ContractModel):
    plan_id: str = Field(min_length=1)
    day_number: int = Field(ge=1)
    activity_index: int = Field(ge=0)
    original_place_id: str = Field(min_length=1)
    candidate_place_id: str = Field(min_length=1)
    activities: list[DraftActivity] = Field(min_length=1)
    transport_segments: list[DraftTransport]

    @model_validator(mode="after")
    def candidate_must_differ(self) -> "EditDraft":
        if self.original_place_id == self.candidate_place_id:
            raise ValueError("候选地点必须与原地点不同")
        return self


class EditDraftResponse(ContractModel):
    kind: Literal["edit_draft"] = "edit_draft"
    message: str = Field(min_length=1)
    draft: EditDraft


ChatResponse = Annotated[
    AnswerResponse | ClarifyResponse | EditTargetResponse | EditDraftResponse,
    Field(discriminator="kind"),
]
chat_response_adapter = TypeAdapter(ChatResponse)
