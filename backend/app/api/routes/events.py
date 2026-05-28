from fastapi import APIRouter, BackgroundTasks, status
from typing import List
import logging
from app.models.telemetry import RuntimeEvent

router = APIRouter()
logger = logging.getLogger(__name__)

def process_telemetry_events(events: List[RuntimeEvent]) -> None:
    """
    Background task to process telemetry events.
    Currently, it logs the events, but can be extended in future phases
    to compile RuntimeState and trigger evaluation pipelines.
    """
    logger.info(f"Asynchronously processing batch of {len(events)} events")
    for event in events:
        logger.info(f"Processing event: {event.event_id} (trace: {event.trace_id}, type: {event.event_type})")

@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(events: List[RuntimeEvent], background_tasks: BackgroundTasks):
    """
    Ingest a batch of runtime telemetry events asynchronously.
    Returns 202 Accepted immediately.
    """
    background_tasks.add_task(process_telemetry_events, events)
    return {"status": "accepted", "message": f"Processing batch of {len(events)} events in the background"}
