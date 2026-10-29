from collections.abc import Callable
from datetime import UTC
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from doctorly.agents.safety import mentions_symptom_or_pain
from doctorly.agents.state import AgentState
from doctorly.core.config import get_settings
from doctorly.core.llm import get_llm
from doctorly.db.session import SessionLocal
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.schemas.agent import RouteDecision
from doctorly.services.retrieval import RetrievalService

NO_FAQ_INFORMATION = "I don't have this information, please call the helpline."
CLARIFYING_RESPONSE = "Could you please rephrase your question?"
BOOKING_PROMPT = "Here are some available appointment slots. Please select a slot."


class StructuredRouter(Protocol):
    def invoke(self, messages: list[BaseMessage]) -> RouteDecision: ...


def _last_user_text(state: AgentState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            if isinstance(message.content, str):
                return message.content
            return str(message.content)
    raise ValueError("Agent state must include a human message")


def _router_model() -> StructuredRouter:
    return get_llm().with_structured_output(RouteDecision)


def _route_system_prompt() -> str:
    return (
        "Classify the latest patient message into exactly one intent: faq for "
        "hospital policy or general hospital information, booking for finding "
        "or selecting an appointment, emergency for possible immediate danger, "
        "or clarifying when the request is unclear. Never diagnose or provide "
        "medical advice. When symptoms could indicate urgent danger, prefer "
        "emergency. Return a confidence from 0 to 1."
    )


def emergency_node(_state: AgentState) -> dict[str, object]:
    message = AIMessage(content=get_settings().emergency_response_template)
    return {
        "messages": [message],
        "intent": "emergency",
        "response": get_settings().emergency_response_template,
        "retrieved_context": [],
        "available_slots": [],
    }


def router_node(
    state: AgentState,
    router_model: StructuredRouter | None = None,
) -> dict[str, object]:
    text = _last_user_text(state)
    decision = (router_model or _router_model()).invoke(
        [
            SystemMessage(content=_route_system_prompt()),
            HumanMessage(content=text),
        ]
    )

    intent = decision.intent
    if decision.confidence < 0.6:
        intent = "emergency" if mentions_symptom_or_pain(text) else "clarifying"

    return {"intent": intent}


def clarifying_node(_state: AgentState) -> dict[str, object]:
    return {
        "messages": [AIMessage(content=CLARIFYING_RESPONSE)],
        "intent": "clarifying",
        "response": CLARIFYING_RESPONSE,
        "retrieved_context": [],
        "available_slots": [],
    }


def make_faq_node(
    session_factory: Callable[[], Session] = SessionLocal,
    retrieval_factory: Callable[[Session], RetrievalService] = RetrievalService,
) -> Callable[[AgentState], dict[str, object]]:
    def faq_node(state: AgentState) -> dict[str, object]:
        settings = get_settings()
        with session_factory() as session:
            documents = retrieval_factory(session).search_faq(
                _last_user_text(state),
                limit=3,
                max_distance=settings.faq_max_cosine_distance,
            )

        context = [
            {
                "title": document.title,
                "content": document.content,
                "source": document.source,
            }
            for document in documents
        ]
        if context:
            answer = "\n\n".join(
                f"{item['title']}\n{item['content']}" for item in context
            )
        else:
            answer = NO_FAQ_INFORMATION

        return {
            "messages": [AIMessage(content=answer)],
            "intent": "faq",
            "retrieved_context": context,
            "available_slots": [],
            "response": answer,
        }

    return faq_node


def make_booking_node(
    session_factory: Callable[[], Session] = SessionLocal,
) -> Callable[[AgentState], dict[str, object]]:
    def booking_node(_state: AgentState) -> dict[str, object]:
        with session_factory() as session:
            slots = AppointmentRepository(session).get_available_slots()[:5]

        available_slots = [
            {
                "id": str(slot.id),
                "doctor_id": str(slot.doctor_id),
                "doctor_name": slot.doctor.display_name,
                "specialty": slot.doctor.specialty,
                "starts_at": slot.starts_at.astimezone(UTC).isoformat(),
                "ends_at": slot.ends_at.astimezone(UTC).isoformat(),
            }
            for slot in slots
        ]
        if available_slots:
            response = BOOKING_PROMPT + "\n" + "\n".join(
                f"{index}. {slot['doctor_name']} ({slot['specialty']}) - "
                f"{slot['starts_at']} (slot ID: {slot['id']})"
                for index, slot in enumerate(available_slots, start=1)
            )
        else:
            response = (
                "There are no available appointment slots right now. "
                "Please try again later or call the helpline."
            )

        return {
            "messages": [AIMessage(content=response)],
            "intent": "booking",
            "retrieved_context": [],
            "available_slots": available_slots,
            "response": response,
        }

    return booking_node


def make_router_node(
    router_model: StructuredRouter | None = None,
) -> Callable[[AgentState], dict[str, object]]:
    def node(state: AgentState) -> dict[str, object]:
        return router_node(state, router_model=router_model)

    return node


def route_from_decision(state: AgentState) -> str:
    intent = state.get("intent")
    if intent not in {"faq", "booking", "emergency", "clarifying"}:
        raise ValueError("Router did not produce a valid intent")
    return intent
