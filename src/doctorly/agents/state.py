from typing import Annotated, Literal, NotRequired, TypedDict
from uuid import UUID

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    patient_id: UUID
    intent: NotRequired[Literal["faq", "booking", "emergency", "clarifying"]]
    retrieved_context: NotRequired[list[dict[str, str]]]
    available_slots: NotRequired[list[dict[str, str]]]
    response: NotRequired[str]
