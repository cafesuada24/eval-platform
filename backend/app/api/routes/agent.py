import os

import yaml
from app.engine.orchestrator import FIXTURES_DIR, load_metric_config
from app.models.config import MetricConfig
from app.services.metric_agent import MetricAgentService
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

METRICS_DIR = os.path.join(FIXTURES_DIR, 'metrics')


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    metric_name: str | None = (
        None  # If provided, load current yaml config to guide the agent
    )


class ChatResponse(BaseModel):
    response_text: str | None
    updated_metric: MetricConfig | None = None


@router.post('/chat', response_model=ChatResponse)
def chat_with_agent(request: ChatRequest):
    agent_service = MetricAgentService()

    current_yaml = None
    if request.metric_name:
        try:
            metric_config = load_metric_config(request.metric_name)
            current_yaml = yaml.dump(
                metric_config.model_dump(exclude_unset=True), sort_keys=False,
            )
        except FileNotFoundError:
            pass  # Metric doesn't exist yet, agent will create it

    messages = [{'role': msg.role, 'content': msg.content} for msg in request.messages]

    try:
        result = agent_service.chat_with_agent(
            messages, current_yaml_config=current_yaml,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    response_text = result.get('response_text')
    called_tool_args = result.get('called_tool_args', [])

    updated_metric = None
    if called_tool_args:
        # Agent decided to update or create a metric config
        tool_args = called_tool_args[-1]  # take the last tool call
        try:
            metric = MetricConfig(**tool_args)

            os.makedirs(METRICS_DIR, exist_ok=True)
            path = os.path.join(METRICS_DIR, f'{metric.name}.yaml')
            with open(path, 'w') as f:
                yaml.dump(metric.model_dump(exclude_unset=True), f, sort_keys=False)

            updated_metric = metric
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f'Failed to parse or save metric config from agent: {str(e)}',
            ) from e

    return ChatResponse(response_text=response_text, updated_metric=updated_metric)
