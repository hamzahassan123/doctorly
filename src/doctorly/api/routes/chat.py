import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

from doctorly.agents.graph import patient_support_graph
from doctorly.core.llm import LLMConfigurationError
from doctorly.core.security import require_patient
from doctorly.models import User
from doctorly.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _event(event_name: str, payload: dict[str, object]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    patient: User = Depends(require_patient),
) -> EventSourceResponse:
    async def event_generator():
        try:
            async for event in patient_support_graph.astream_events(
                {
                    "messages": [HumanMessage(content=request.message)],
                    "patient_id": patient.id,
                },
                version="v1",
                stream_mode="updates",
            ):
                if event.get("event") != "on_chain_end":
                    continue

                output = event.get("data", {}).get("output")
                if not isinstance(output, dict):
                    continue

                payload = {
                    "intent": output.get("intent", "faq"),
                    "response": output.get("response", ""),
                    "retrieved_context": output.get("retrieved_context", []),
                    "available_slots": output.get("available_slots", []),
                }
                if payload["response"]:
                    yield _event("message", payload)
                    break
            yield _event("done", {"status": "complete"})
        except LLMConfigurationError as exc:
            logger.exception("Chat stream could not start because the LLM is not configured")
            yield _event(
                "error",
                {"detail": "Patient chat is not configured"},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Patient chat is not configured",
            ) from exc
        except Exception:
            logger.exception("Chat stream failed")
            yield _event("error", {"detail": "Chat stream failed"})

    return EventSourceResponse(event_generator())
