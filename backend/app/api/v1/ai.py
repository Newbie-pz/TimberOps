"""Read-only TimberOps Agent endpoint with a bounded execution time."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from langchain_openai.chat_models.base import (
    OpenAIConnectionError,
    OpenAITimeoutError,
)
from openai import APIError, APITimeoutError

from app.core.config import Settings, get_settings
from app.integrations.ai.agent.graph import TimberOpsAgent
from app.integrations.ai.dependencies import get_ai_agent
from app.integrations.ai.exceptions import (
    AIAgentError,
    AIIntegrationError,
    AIUpstreamError,
    AIUpstreamTimeoutError,
)
from app.schemas.ai import AIChatRequest, AIChatResponse, AIToolCallRead
from app.security.permissions import require_permission


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/chat",
    response_model=AIChatResponse,
    dependencies=[Depends(require_permission("ai:query"))],
)
async def chat(
    payload: AIChatRequest,
    request: Request,
    agent: Annotated[TimberOpsAgent, Depends(get_ai_agent)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIChatResponse:
    """Answer one question through model-selected, read-only business tools."""
    request.state.ai_message_length = len(payload.message)
    try:
        async with asyncio.timeout(settings.ai_agent_timeout_seconds):
            result = await agent.achat(payload.message)
    except (TimeoutError, APITimeoutError, OpenAITimeoutError) as exc:
        raise AIUpstreamTimeoutError from exc
    except (APIError, OpenAIConnectionError) as exc:
        raise AIUpstreamError from exc
    except AIIntegrationError:
        raise
    except Exception as exc:
        raise AIAgentError from exc

    request.state.ai_tool_names = [tool_call.name for tool_call in result.tool_calls]
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
