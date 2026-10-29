from typing import Literal

from pydantic import Field

from doctorly.schemas.common import ApiSchema


class RouteDecision(ApiSchema):
    intent: Literal["faq", "booking", "emergency", "clarifying"]
    confidence: float = Field(ge=0, le=1)
