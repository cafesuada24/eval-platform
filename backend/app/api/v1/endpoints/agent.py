from typing import Annotated
from uuid import UUID

from app.api.dependencies import (
    get_chat_session_repo,
    get_metric_helper_app_service,
)
from app.api.v1.schemas.agent_dtos import ChatRequest, SaveSessionRequest
from app.core.agents.metric_helper.models import (
    ChatSession,
    MetricHelperResponse,
)
from app.core.agents.metric_helper.ports import (
    ChatSessionRepository,
)
from app.core.agents.metric_helper.services import MetricHelperAppService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.get('/sessions/{metric_id}', response_model=ChatSession)
def get_session(
    metric_id: UUID,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repo)],
) -> ChatSession:
    """Retrieve the persisted chat session history for a metric."""
    session = session_repo.find_by_id(metric_id)
    if not session:
        return ChatSession(metric_id=metric_id, messages=[])
    return session


@router.delete('/sessions/{metric_id}')
def delete_session(
    metric_id: UUID,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repo)],
) -> dict[str, str]:
    """Clear the persisted chat session history for a metric."""
    try:
        session_repo.delete(metric_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to clear session: {str(e)}',
        ) from e
    return {
        'status': 'success',
        'message': f"Session for metric '{metric_id}' cleared.",
    }


@router.post('/sessions/{metric_id}')
def save_session(
    metric_id: UUID,
    request: SaveSessionRequest,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repo)],
) -> dict[str, str]:
    """Explicitly save the chat session history for a metric (e.g. upon creation)."""
    try:
        session_data = ChatSession(metric_id=metric_id, messages=request.messages)
        session_repo.save(session_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to save session: {str(e)}',
        ) from e
    return {
        'status': 'success',
        'message': f"Session for metric '{metric_id}' saved.",
    }


@router.post('/chat', response_model=MetricHelperResponse)
async def chat_with_agent(
    request: ChatRequest,
    app_service: Annotated[MetricHelperAppService, Depends(get_metric_helper_app_service)],
) -> MetricHelperResponse:
    try:
        return await app_service.chat(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during chat: {str(e)}") from e
