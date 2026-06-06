"""Runtime related events."""

from typing import Annotated
from uuid import UUID, uuid4

from app.api.dependencies import get_runtime_state_repo
from app.api.v1.schemas.events import EventGetResponse
from app.api.v1.schemas.runtimes import (
    RuntimeIngestionRequest,
    RuntimeIngestionResponse,
    RuntimeStateGetResponse,
)
from app.core.eval_engine.extractors.runtime_state_extractor import (
    RuntimeStateExtractorService,
)
from app.core.eval_engine.models import EvaluationContext, TestCase
from app.core.exceptions import NotFoundError
from app.core.kernel.models import RuntimeEvent, RuntimeState
from app.core.kernel.ports import RuntimeStateRepository
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter()


@router.put('')
async def ingest_runtime(
    request: RuntimeIngestionRequest,
    repository: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
) -> RuntimeIngestionResponse:
    """Ingest a runtime."""
    events = [
        RuntimeEvent(
            runtime_id=ev.runtime_id,
            payload=ev.payload,
            timestamp=ev.timestamp,
        )
        for ev in request.events
    ]

    state = RuntimeState(
        runtime_id=request.runtime_id or uuid4(),
        events=events,
        resource_usage=request.usage,
        metadata=request.metadata,
    )

    repository.save(state)

    return RuntimeIngestionResponse(runtime_id=state.runtime_id)


@router.post('')
async def ingest_runtimes_batch(
    requests: list[RuntimeIngestionRequest],
    repository: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
) -> list[RuntimeIngestionResponse]:
    """Ingest a batch of runtimes."""
    responses: list[RuntimeIngestionResponse] = []
    for request in requests:
        events = [
            RuntimeEvent(
                runtime_id=ev.runtime_id,
                payload=ev.payload,
                timestamp=ev.timestamp,
            )
            for ev in request.events
        ]

        print(len(events))

        state = RuntimeState(
            runtime_id=request.runtime_id or uuid4(),
            events=events,
            resource_usage=request.usage,
            metadata=request.metadata,
        )

        repository.save(state)
        responses.append(RuntimeIngestionResponse(runtime_id=state.runtime_id))

    return responses


@router.get('')
def list_runtimes(
    repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
) -> list[RuntimeStateGetResponse]:
    """List all runtime state traces."""
    return [
        RuntimeStateGetResponse(
            runtime_id=rt.runtime_id,
            usage=rt.resource_usage,
            events=[
                EventGetResponse(
                    event_id=ev.event_id,
                    runtime_id=rt.runtime_id,
                    payload=ev.payload,
                    timestamp=ev.timestamp,
                )
                for ev in rt.events
            ],
            metadata=rt.metadata,
        )
        for rt in repo.list_all()
    ]


@router.get('/{runtime_id}')
def get_runtime(
    runtime_id: UUID,
    repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
) -> RuntimeStateGetResponse:
    """Get a specific runtime state trace by ID."""
    try:
        rt = repo.get_by_id(runtime_id)

        return RuntimeStateGetResponse(
            runtime_id=rt.runtime_id,
            usage=rt.resource_usage,
            events=[
                EventGetResponse(
                    event_id=ev.event_id,
                    runtime_id=rt.runtime_id,
                    payload=ev.payload,
                    timestamp=ev.timestamp,
                )
                for ev in rt.events
            ],
            metadata=rt.metadata,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get('/{runtime_id}/variables')
def get_runtime_variables(
    runtime_id: UUID,
    repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
    keys: str | None = Query(
        None,
        description='Comma-separated list of variable names to extract',
    ),
) -> dict[str, str | int | float | None]:
    """Extract specific or all variables from a runtime state trace."""
    try:
        state = repo.get_by_id(runtime_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    supported_vars = RuntimeStateExtractorService.get_supported_runtime_variables()
    vars_to_extract = supported_vars

    if keys:
        requested_keys = [k.strip() for k in keys.split(',')]
        vars_to_extract = [k for k in requested_keys if k in supported_vars]

    result: dict[str, str | int | float | None] = {}
    context = EvaluationContext(
        test_case=TestCase(
            id=uuid4(),
            inputs={},
            expected_outputs={},
            metadata={},
        ),
        runtime_states=[state],
    )

    for var in vars_to_extract:
        val = RuntimeStateExtractorService.extract_variable(var, context)
        if val is not None:
            result[var] = val

    return result


@router.delete('/{runtime_id}')
def delete_runtime(
    runtime_id: UUID,
    repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
) -> dict[str, str]:
    """Delete a runtime state trace."""
    try:
        repo.delete(runtime_id)
        return {'status': 'success', 'message': f'Runtime state {runtime_id} deleted.'}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to delete runtime state: {str(e)}',
        ) from e
