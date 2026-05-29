import contextlib
import json
import os

import yaml
from app.engine.orchestrator import FIXTURES_DIR, load_metric_config
from app.models.agent import ChatMessage, ChatSession
from app.models.config import MetricConfig
from app.services.metric_agent import MetricAgentService
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

METRICS_DIR = os.path.join(FIXTURES_DIR, 'metrics')
SESSIONS_DIR = os.path.join(FIXTURES_DIR, 'sessions')


class ChatRequest(BaseModel):
    message: str | None = None  # Single new user message
    messages: list[ChatMessage] | None = None  # Optional full history override
    metric_name: str | None = None  # The metric name to bind to a persisted session


class ChatResponse(BaseModel):
    response_text: str | None = None
    updated_metric: MetricConfig | None = None
    messages: list[ChatMessage] | None = None  # The complete message history


@router.get('/sessions/{metric_name}', response_model=ChatSession)
def get_session(metric_name: str) -> ChatSession:
    """Retrieve the persisted chat session history for a metric."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    path = os.path.join(SESSIONS_DIR, f'{metric_name}.json')
    if not os.path.exists(path):
        return ChatSession(metric_name=metric_name, messages=[])

    try:
        with open(path) as f:
            data = json.load(f)
        return ChatSession(**data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to load session: {str(e)}',
        ) from e


@router.delete('/sessions/{metric_name}')
def delete_session(metric_name: str) -> dict[str, str]:
    """Clear the persisted chat session history for a metric."""
    path = os.path.join(SESSIONS_DIR, f'{metric_name}.json')
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f'Failed to clear session: {str(e)}',
            ) from e
    return {
        'status': 'success',
        'message': f"Session for metric '{metric_name}' cleared.",
    }


@router.post('/chat')
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    agent_service = MetricAgentService()

    current_yaml = None
    metric_name = request.metric_name
    if metric_name:
        try:
            metric_config = load_metric_config(metric_name)
            current_yaml = yaml.dump(
                metric_config.model_dump(exclude_unset=True),
                sort_keys=False,
            )
        except FileNotFoundError:
            pass  # Metric doesn't exist yet, agent will create it

    # Resolve message history
    messages_list: list[ChatMessage] = []

    if metric_name:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        session_path = os.path.join(SESSIONS_DIR, f'{metric_name}.json')

        # If client provided full history explicitly, override/use it
        if request.messages is not None and len(request.messages) > 0:
            messages_list = request.messages
        # Otherwise, attempt to load persisted history
        elif os.path.exists(session_path):
            try:
                with open(session_path) as f:
                    session_data = json.load(f)
                    messages_list = [
                        ChatMessage(**m) for m in session_data.get('messages', [])
                    ]
            except Exception:
                messages_list = []
    else:
        # Backwards compatibility: use request.messages
        messages_list = request.messages or []

    # Append the single new message if provided
    if request.message:
        messages_list.append(ChatMessage(role='user', content=request.message))

    if not messages_list:
        raise HTTPException(
            status_code=400,
            detail='No message or message history provided in request.',
        )

    # Format messages for the Gemini SDK call, excluding system-generated [Test Run] logs from conversational history
    formatted_messages = [
        {'role': msg.role, 'content': msg.content} for msg in messages_list
        if not msg.content.startswith('[Test Run]')
    ]

    try:
        result = agent_service.chat_with_agent(
            formatted_messages,
            current_yaml_config=current_yaml,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    response_text = result.get('response_text')
    updated_metric_data = result.get('updated_metric')

    # Append the agent's reply to the message history
    if response_text:
        messages_list.append(ChatMessage(role='model', content=response_text))

    updated_metric = None
    if updated_metric_data:
        with contextlib.suppress(Exception):
            updated_metric = MetricConfig(**updated_metric_data)

    # Persist updated session if we have a resolved metric name (passed in request or newly created draft)
    resolved_metric_name = metric_name or (
        updated_metric.name if updated_metric else None
    )
    if resolved_metric_name:
        try:
            os.makedirs(SESSIONS_DIR, exist_ok=True)
            session_path = os.path.join(SESSIONS_DIR, f'{resolved_metric_name}.json')
            session_data = ChatSession(
                metric_name=resolved_metric_name, messages=messages_list,
            )
            with open(session_path, 'w') as f:
                json.dump(session_data.model_dump(), f, indent=2)
        except Exception:
            # Non-blocking if persistence fails
            pass

    return ChatResponse(
        response_text=response_text,
        updated_metric=updated_metric,
        messages=messages_list,
    )
