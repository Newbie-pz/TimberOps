"""Read-only TimberOps Agent endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.integrations.ai.agent.graph import TimberOpsAgent
from app.integrations.ai.dependencies import get_ai_agent
from app.schemas.ai import AIChatRequest, AIChatResponse, AIToolCallRead


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AIChatResponse)
def chat(
    payload: AIChatRequest,
    agent: Annotated[TimberOpsAgent, Depends(get_ai_agent)],
) -> AIChatResponse:
    """Answer one question through model-selected, read-only business tools."""
    result = agent.chat(payload.message)
    return AIChatResponse(
        answer=result.answer,
        tool_calls=[
            AIToolCallRead(
                name=tool_call.name,
                arguments=tool_call.arguments,
                status=tool_call.status,
            )
            for tool_call in result.tool_calls
        ],
    )
