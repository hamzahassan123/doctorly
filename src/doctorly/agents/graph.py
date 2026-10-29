from collections.abc import Callable

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from doctorly.agents.nodes import (
    StructuredRouter,
    clarifying_node,
    emergency_node,
    make_booking_node,
    make_faq_node,
    make_router_node,
    route_from_decision,
)
from doctorly.agents.safety import is_emergency
from doctorly.agents.state import AgentState
from doctorly.db.session import SessionLocal
from doctorly.services.retrieval import RetrievalService

SessionFactory = Callable[[], Session]


def _route_initial_message(state: AgentState) -> str:
    human_message = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )
    if human_message is None or not isinstance(human_message.content, str):
        raise ValueError("Agent state must include a text human message")
    return "emergency" if is_emergency(human_message.content) else "router"


def build_patient_support_graph(
    *,
    session_factory: SessionFactory = SessionLocal,
    router_model: StructuredRouter | None = None,
    retrieval_factory: Callable[[Session], RetrievalService] = RetrievalService,
):
    builder = StateGraph(AgentState)
    builder.add_node("emergency_node", emergency_node)
    builder.add_node("router_node", make_router_node(router_model))
    builder.add_node("faq_node", make_faq_node(session_factory, retrieval_factory))
    builder.add_node("booking_node", make_booking_node(session_factory))
    builder.add_node("clarifying_node", clarifying_node)
    builder.add_conditional_edges(
        START,
        _route_initial_message,
        {"emergency": "emergency_node", "router": "router_node"},
    )
    builder.add_conditional_edges(
        "router_node",
        route_from_decision,
        {
            "faq": "faq_node",
            "booking": "booking_node",
            "emergency": "emergency_node",
            "clarifying": "clarifying_node",
        },
    )
    for node_name in (
        "emergency_node",
        "faq_node",
        "booking_node",
        "clarifying_node",
    ):
        builder.add_edge(node_name, END)
    return builder.compile()


patient_support_graph = build_patient_support_graph()
