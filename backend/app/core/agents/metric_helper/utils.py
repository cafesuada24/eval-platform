"""Utilities for metric helper."""

import yaml
from app.core.agents.metric_helper.models import AgentEvent, Thread


def stringifyToYaml(obj: object) -> str:
    """Convert an object to a string of YAML."""
    data = obj if isinstance(obj, dict) else vars(obj)
    dumped_yaml = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
    )
    return '\n'.join('  ' + line for line in dumped_yaml.splitlines())


def event_to_prompt(event: AgentEvent) -> str:
    """Convert an event to XML tag format."""
    data = event.data if isinstance(event.data, str) else stringifyToYaml(event.data)
    return f'<{event.type}>\n{data}\n</{event.type}>'


def thread_to_prompt(thread: Thread) -> str:
    """Convert a thread to XML tag format."""
    return '\n\n'.join(event_to_prompt(event) for event in thread.events)
