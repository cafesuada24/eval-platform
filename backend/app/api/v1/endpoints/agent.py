import uuid
from typing import Annotated
from uuid import UUID

import yaml
from app.api.dependencies import (
    get_agentic_helper,
    get_chat_session_repo,
    get_metric_repo,
)
from app.api.v1.schemas.agent_dtos import ChatRequest
from app.core.agents.metric_helper.models import (
    ChatMessage,
    ChatSession,
    MetricHelperResponse,
)
from app.core.agents.metric_helper.ports import (
    AgenticMetricHelper,
    ChatSessionRepository,
)
from app.core.eval_engine.models import Metric
from app.core.eval_engine.ports import MetricRepository
from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter

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


@router.post('/chat', response_model=MetricHelperResponse)
async def chat_with_agent(
    request: ChatRequest,
    agentic_builder: Annotated[AgenticMetricHelper, Depends(get_agentic_helper)],
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repo)],
) -> MetricHelperResponse:
    current_yaml = None
    metric_id = request.metric_id

    if metric_id:
        metric_config = metric_repo.find_by_id(metric_id)
        if metric_config:
            data = TypeAdapter(Metric).dump_python(
                metric_config,
                mode='json',
                exclude_none=True,
            )
            current_yaml = yaml.dump(data, sort_keys=False)

    messages_list: list[ChatMessage] = []

    if metric_id:
        if request.messages is not None and len(request.messages) > 0:
            messages_list = request.messages
        else:
            session = session_repo.find_by_id(metric_id)
            if session:
                messages_list = session.messages
    else:
        messages_list = request.messages or []
        metric_id = uuid.uuid4()

    if request.message:
        messages_list.append(ChatMessage(role='user', content=request.message))

    if not messages_list:
        raise HTTPException(
            status_code=400, detail='No message or message history provided in request.',
        )

    # Filter out test runs
    formatted_messages = [
        msg for msg in messages_list if not msg.content.startswith('[Test Run]')
    ]

    session = ChatSession(metric_id=metric_id, messages=formatted_messages)

    try:
        result = await agentic_builder.chat(
            session=session,
            current_metric_config=current_yaml,
        )
    except Exception as e:
        raise

    if result.response_text:
        messages_list.append(ChatMessage(role='model', content=result.response_text))

    try:
        session_data = ChatSession(metric_id=metric_id, messages=messages_list)
        session_repo.save(session_data)
    except Exception as e:
        print(f'Failed to save session: {e}')

    return result
