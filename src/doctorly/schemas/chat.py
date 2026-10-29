from pydantic import Field
from typing import Literal

from doctorly.schemas.common import ApiSchema


class ChatRequest(ApiSchema):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(ApiSchema):
    intent: Literal["faq", "booking", "emergency", "clarifying"]
    response: str
    retrieved_context: list[dict[str, str]]
    available_slots: list[dict[str, str]]
