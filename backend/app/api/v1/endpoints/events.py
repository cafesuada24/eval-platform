import logging
from typing import Annotated
from uuid import UUID

from app.api.dependencies import get_runtime_state_repo
from app.core.kernel.models import RuntimeEvent, RuntimeState
from app.core.kernel.ports import RuntimeStateRepository
from fastapi import APIRouter, BackgroundTasks, Depends, status

router = APIRouter()
logger = logging.getLogger(__name__)


def process_telemetry_events(
    events: list[RuntimeEvent],
    repo: RuntimeStateRepository,
) -> None:
    """Background task to process telemetry events.

    Groups events by runtime_id and persists them to the RuntimeStateRepository.
    """
    logger.info(f'Asynchronously processing batch of {len(events)} events')

    # Group by runtime_id
    grouped_events: dict[UUID, list[RuntimeEvent]] = {}
    for event in events:
        if event.runtime_id not in grouped_events:
            grouped_events[event.runtime_id] = []
        grouped_events[event.runtime_id].append(event)

    for runtime_id, event_group in grouped_events.items():
        state = repo.find_by_id(runtime_id)
        if not state:
            state = RuntimeState(runtime_id=runtime_id, events=[])

        state.events.extend(event_group)
        repo.save(state)
        logger.info(f'Saved {len(event_group)} events to trace {runtime_id}')


@router.post('', status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(
    events: list[RuntimeEvent],
    background_tasks: BackgroundTasks,
    repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
):
    """Ingest a batch of runtime telemetry events asynchronously.

    Returns 202 Accepted immediately.
    """
    background_tasks.add_task(process_telemetry_events, events, repo)
    return {
        'status': 'accepted',
        'message': f'Processing batch of {len(events)} events in the background',
    }
