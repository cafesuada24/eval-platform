"""Dependency injection for the API layer."""

from functools import lru_cache
from typing import Annotated

from app.core.agents.metric_helper.ports import (
    AgenticMetricHelper,
    ChatSessionRepository,
)
from app.core.agents.metric_helper.services import MetricHelperAppService
from app.core.config import settings
from app.core.documents.ports import DocumentRepository
from app.core.documents.services import DocumentService
from app.core.eval_engine.extractors.runtime_state_extractor import (
    RuntimeStateExtractorService,
)
from app.core.eval_engine.ports import (
    AIJudgeService,
    BatchResultRepository,
    DatasetRepository,
    MetricRepository,
    PipelineRepository,
)
from app.core.eval_engine.services.dataset_parser import DatasetParserService
from app.core.eval_engine.services.evaluation_orchestrator import EvaluationOrchestratorService
from app.core.eval_engine.services.formula_evaluator import FormulaEvaluatorService
from app.core.eval_engine.services.metric_evaluator import MetricEvaluatorService
from app.core.eval_engine.services.pipeline_evaluator import PipelineEvaluatorService
from app.core.kernel.ports import RuntimeStateRepository
from app.core.vector_storage.ports import VectorStoragePort
from app.infra.agents.metric_helper_agent import GeminiMetricHelper
from app.infra.repositories.json_batch_result_repository import (
    LocalJsonBatchResultRepository,
)
from app.infra.repositories.json_chat_session_repository import (
    LocalJsonChatSessionRepository,
)
from app.infra.repositories.json_dataset_repository import LocalJsonDatasetRepository
from app.infra.repositories.json_document_repository import LocalJsonDocumentRepository
from app.infra.repositories.yaml_metric_repository import YamlMetricRepository
from app.infra.repositories.yaml_pipeline_repository import YamlPipelineRepository
from app.infra.repositories.yaml_runtimestate_repository import (
    YamlRuntimeStateRepository,
)
from app.infra.services.ai_judge_service import LiteLLMAIJudge
from app.infra.vector_storage.chroma_adapter import ChromaVectorStorage
from fastapi import Depends


@lru_cache
def get_metric_repo() -> MetricRepository:
    """Get the metric repository singleton."""
    return YamlMetricRepository(settings.metrics_dir)


@lru_cache
def get_pipeline_repo() -> PipelineRepository:
    """Get the pipeline repository singleton."""
    return YamlPipelineRepository(settings.pipelines_dir)


@lru_cache
def get_runtime_state_repo() -> RuntimeStateRepository:
    """Get the runtime state repository singleton."""
    return YamlRuntimeStateRepository(settings.runtimes_dir)

@lru_cache
def get_chat_session_repo() -> ChatSessionRepository:
    """Get the chat session repository singleton."""
    return LocalJsonChatSessionRepository(settings.sessions_dir)

@lru_cache
def get_dataset_repo() -> DatasetRepository:
    """Get the dataset repository singleton."""
    return LocalJsonDatasetRepository(settings.datasets_dir)

@lru_cache
def get_batch_result_repo() -> BatchResultRepository:
    """Get the batch result repository singleton."""
    return LocalJsonBatchResultRepository(settings.batch_results_dir)

@lru_cache
def get_document_repo() -> DocumentRepository:
    """Get the document repository singleton."""
    return LocalJsonDocumentRepository(settings.uploads_dir)


@lru_cache
def get_vector_storage() -> VectorStoragePort:
    """Get the vector storage singleton."""
    return ChromaVectorStorage(settings.chromadb_dir)


def get_document_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    vector_storage: Annotated[VectorStoragePort, Depends(get_vector_storage)],
) -> DocumentService:
    """Get the document service."""
    return DocumentService(document_repo=document_repo, vector_storage=vector_storage)


@lru_cache
def get_ai_judge_service() -> AIJudgeService:
    """Get the AI judge service singleton."""
    return LiteLLMAIJudge()


def get_metric_evaluator(
    ai_judge: Annotated[AIJudgeService, Depends(get_ai_judge_service)],
) -> MetricEvaluatorService:
    """Get the metric evaluator service."""
    return MetricEvaluatorService(
        rs_extractor=RuntimeStateExtractorService(),
        formula_evaluator=FormulaEvaluatorService(),
        ai_judge_service=ai_judge,
    )


def get_pipeline_evaluator(
    metric_evaluator: Annotated[MetricEvaluatorService, Depends(get_metric_evaluator)],
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
) -> PipelineEvaluatorService:
    """Get the pipeline evaluator service."""
    return PipelineEvaluatorService(
        metric_eval_srv=metric_evaluator,
        metric_repo=metric_repo,
    )


def get_evaluation_orchestrator(
    batch_result_repo: Annotated[BatchResultRepository, Depends(get_batch_result_repo)],
    pipeline_eval_srv: Annotated[PipelineEvaluatorService, Depends(get_pipeline_evaluator)],
    runtime_state_repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> EvaluationOrchestratorService:
    """Get the evaluation orchestrator service."""
    return EvaluationOrchestratorService(
        batch_result_repo=batch_result_repo,
        pipeline_eval_srv=pipeline_eval_srv,
        runtime_state_repo=runtime_state_repo,
        dataset_repo=dataset_repo,
    )


def get_dataset_parser() -> DatasetParserService:
    """Get the dataset parser service."""
    return DatasetParserService()


def get_agentic_helper(
    runtime_repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
    vector_storage: Annotated[VectorStoragePort, Depends(get_vector_storage)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
) -> AgenticMetricHelper:
    """Get the agentic builder."""
    return GeminiMetricHelper(
        runtime_state_repo=runtime_repo,
        vector_storage=vector_storage,
        document_repo=document_repo,
    )


def get_metric_helper_app_service(
    agentic_helper: Annotated[AgenticMetricHelper, Depends(get_agentic_helper)],
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repo)],
) -> MetricHelperAppService:
    """Get the metric helper application service."""
    return MetricHelperAppService(
        agentic_helper=agentic_helper,
        metric_repo=metric_repo,
        session_repo=session_repo,
    )
