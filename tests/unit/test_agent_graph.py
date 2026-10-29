from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import HumanMessage

from doctorly.agents.graph import build_patient_support_graph
from doctorly.agents.safety import is_emergency, mentions_symptom_or_pain
from doctorly.core.config import get_settings
from doctorly.schemas.agent import RouteDecision


def test_is_emergency_detects_english_roman_urdu_and_urdu() -> None:
    assert is_emergency("I have severe chest pain")
    assert is_emergency("saans nahi aa rahi")
    assert is_emergency("seene mein dard ho raha hai")
    assert is_emergency("سینے میں درد ہو رہا ہے")
    assert is_emergency("شدید خون بہہ رہا ہے")


def test_emergency_appointment_without_symptoms_is_not_emergency() -> None:
    assert not is_emergency("I need an emergency appointment")
    assert not mentions_symptom_or_pain("I need an emergency appointment")


def test_low_confidence_symptoms_route_to_emergency() -> None:
    assert mentions_symptom_or_pain("I have a mild headache")
    assert not is_emergency("I have a mild headache")


class FakeRouter:
    def __init__(self, decision: RouteDecision | None = None) -> None:
        self.decision = decision
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        assert isinstance(messages[-1], HumanMessage)
        if self.decision is None:
            raise AssertionError("Emergency input must bypass the router")
        return self.decision


def test_emergency_query_bypasses_router_and_uses_fixed_response() -> None:
    response_text = get_settings().emergency_response_template
    router = FakeRouter()
    graph = build_patient_support_graph(router_model=router)

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="I have severe chest pain")],
            "patient_id": uuid4(),
        }
    )

    assert router.calls == 0
    assert result["intent"] == "emergency"
    assert result["response"] == response_text
    assert "Emergency Department" in result["response"]
    assert "Rescue 1122" in result["response"]
    assert "Edhi 115" in result["response"]
    assert "Do not wait" in result["response"]


def test_faq_query_routes_to_retrieved_context_only() -> None:
    router = FakeRouter(RouteDecision(intent="faq", confidence=0.95))
    expected_title = "Appointment cancellation policy"
    expected_content = "Patients may cancel up to 12 hours before the appointment."

    class FakeRetrieval:
        def search_faq(self, query, *, limit, max_distance):
            assert query == "How can I cancel?"
            assert limit == 3
            assert max_distance == get_settings().faq_max_cosine_distance
            return [
                SimpleNamespace(
                    title=expected_title,
                    content=expected_content,
                    source="hospital_kb.json",
                )
            ]

    graph = build_patient_support_graph(
        router_model=router,
        session_factory=lambda: nullcontext(object()),
        retrieval_factory=lambda _session: FakeRetrieval(),
    )

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="How can I cancel?")],
            "patient_id": uuid4(),
        }
    )

    assert router.calls == 1
    assert result["intent"] == "faq"
    assert expected_title in result["response"]
    assert expected_content in result["response"]
    assert "I can help with that" not in result["response"]
    assert result["retrieved_context"] == [
        {
            "title": expected_title,
            "content": expected_content,
            "source": "hospital_kb.json",
        }
    ]


def test_low_confidence_non_medical_query_routes_to_clarification() -> None:
    router = FakeRouter(RouteDecision(intent="faq", confidence=0.4))
    graph = build_patient_support_graph(router_model=router)

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Can you do the thing?")],
            "patient_id": uuid4(),
        }
    )

    assert result["intent"] == "clarifying"
    assert result["response"] == "Could you please rephrase your question?"


def test_low_confidence_symptom_query_routes_to_emergency() -> None:
    router = FakeRouter(RouteDecision(intent="faq", confidence=0.4))
    graph = build_patient_support_graph(router_model=router)

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="I have a headache")],
            "patient_id": uuid4(),
        }
    )

    assert result["intent"] == "emergency"
    assert "Emergency Department" in result["response"]
