"""Management clients for datasets, pipelines, and evaluations."""

import contextvars
import logging
import os
import threading
import warnings
from collections.abc import Generator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Final, Self

import httpx

# We use strings for runtime_ids to avoid continuous UUID parsing overhead.
type RuntimeId = str

logger: Final = logging.getLogger(__name__)

# ContextVar to automatically track runtimes created during an evaluation case
current_evaluation_runtimes: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    'current_evaluation_runtimes', default=None
)


class DatasetClient:
    """Client for managing datasets."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        """Initialize the DatasetClient."""
        self._client = client
        self._base_url = base_url.rstrip('/')

    def upload_json(self, name: str, file_path: str) -> Mapping[str, Any]:
        """Uploads a JSON dataset."""
        return self._upload_file(name, file_path, 'application/json')

    def upload_csv(self, name: str, file_path: str) -> Mapping[str, Any]:
        """Uploads a CSV dataset."""
        return self._upload_file(name, file_path, 'text/csv')

    def _upload_file(
        self,
        name: str,
        file_path: str,
        content_type: str,
    ) -> Mapping[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'Dataset file not found: {file_path}')

        with open(file_path, 'rb') as f:
            files = {'file': (name, f, content_type)}
            response = self._client.post(f'{self._base_url}/v1/datasets/upload', files=files)
            response.raise_for_status()
            return response.json()

    def list_datasets(self) -> list[Mapping[str, Any]]:
        """Lists all datasets in the system."""
        response = self._client.get(f'{self._base_url}/v1/datasets')
        response.raise_for_status()
        return response.json()

    def get_dataset(self, dataset_id: str) -> Mapping[str, Any]:
        """Retrieves details of a specific dataset."""
        response = self._client.get(f'{self._base_url}/v1/datasets/{dataset_id}')
        response.raise_for_status()
        return response.json()

    def get_cases(self, dataset_id: str) -> list[Mapping[str, Any]]:
        """Retrieves test cases for a given dataset."""
        data = self.get_dataset(dataset_id)
        return data.get('cases', [])

    def create_dataset(self, name: str, schema: Mapping[str, Any]) -> Mapping[str, Any]:
        """Creates a new empty dataset."""
        response = self._client.post(
            f'{self._base_url}/v1/datasets/',
            json={'name': name, 'schema_': schema}
        )
        response.raise_for_status()
        return response.json()

    def update_dataset(self, dataset_id: str, name: str, schema: Mapping[str, Any]) -> Mapping[str, Any]:
        """Updates dataset metadata."""
        response = self._client.patch(
            f'{self._base_url}/v1/datasets/{dataset_id}',
            json={'name': name, 'schema_': schema}
        )
        response.raise_for_status()
        return response.json()

    def add_testcase(
        self,
        dataset_id: str,
        inputs: Mapping[str, Any],
        expected_outputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Adds a new testcase to a dataset."""
        response = self._client.post(
            f'{self._base_url}/v1/datasets/{dataset_id}/cases',
            json={
                'inputs': inputs,
                'expected_outputs': expected_outputs or {},
                'metadata': metadata or {},
            }
        )
        response.raise_for_status()
        return response.json()

    def update_testcase(
        self,
        dataset_id: str,
        case_id: str,
        inputs: Mapping[str, Any],
        expected_outputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Updates an existing testcase in a dataset."""
        response = self._client.put(
            f'{self._base_url}/v1/datasets/{dataset_id}/cases/{case_id}',
            json={
                'inputs': inputs,
                'expected_outputs': expected_outputs or {},
                'metadata': metadata or {},
            }
        )
        response.raise_for_status()
        return response.json()

    def delete_testcase(self, dataset_id: str, case_id: str) -> None:
        """Deletes a testcase from a dataset."""
        response = self._client.delete(f'{self._base_url}/v1/datasets/{dataset_id}/cases/{case_id}')
        response.raise_for_status()

    def upload_file(
        self,
        dataset_id: str,
        file_name: str,
        file_path: str,
        content_type: str = 'application/octet-stream',
    ) -> Mapping[str, Any]:
        """Uploads a raw data file for a dataset."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found: {file_path}')
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f, content_type)}
            response = self._client.post(f'{self._base_url}/v1/datasets/{dataset_id}/files', files=files)
            response.raise_for_status()
            return response.json()

    def delete_dataset_file(self, dataset_id: str, file_id: str) -> None:
        """Deletes an uploaded dataset file."""
        response = self._client.delete(f'{self._base_url}/v1/datasets/{dataset_id}/files/{file_id}')
        response.raise_for_status()

    def download_file(self, dataset_id: str, file_id: str) -> bytes:
        """Downloads a dataset file and returns its raw binary contents."""
        response = self._client.get(f'{self._base_url}/v1/datasets/{dataset_id}/files/{file_id}')
        response.raise_for_status()
        return response.content

    def download_file_to_disk(self, dataset_id: str, file_id: str, dest_path: str) -> None:
        """Downloads a dataset file and saves it directly to a local disk path."""
        content = self.download_file(dataset_id, file_id)
        with open(dest_path, 'wb') as f:
            f.write(content)


class MetricClient:
    """Client for managing metrics configurations."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip('/')

    def list_metrics(self) -> list[Mapping[str, Any]]:
        """Lists all configured metrics."""
        response = self._client.get(f'{self._base_url}/v1/configs/metrics')
        response.raise_for_status()
        return response.json()

    def get_metric(self, metric_id: str) -> Mapping[str, Any]:
        """Retrieves a specific metric by ID."""
        response = self._client.get(f'{self._base_url}/v1/configs/metrics/{metric_id}')
        response.raise_for_status()
        return response.json()

    def create_metric(self, metric: Mapping[str, Any]) -> Mapping[str, Any]:
        """Creates a new metric configuration."""
        response = self._client.post(f'{self._base_url}/v1/configs/metrics', json=metric)
        response.raise_for_status()
        return response.json()

    def update_metric(self, metric_id: str, metric: Mapping[str, Any]) -> Mapping[str, Any]:
        """Updates an existing metric configuration."""
        response = self._client.put(f'{self._base_url}/v1/configs/metrics/{metric_id}', json=metric)
        response.raise_for_status()
        return response.json()

    def delete_metric(self, metric_id: str) -> None:
        """Deletes a metric configuration."""
        response = self._client.delete(f'{self._base_url}/v1/configs/metrics/{metric_id}')
        response.raise_for_status()


class PipelineClient:
    """Client for managing pipelines."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip('/')

    def list_pipelines(self) -> list[Mapping[str, Any]]:
        """Lists all configured pipelines."""
        response = self._client.get(f'{self._base_url}/v1/configs/pipelines')
        response.raise_for_status()
        return response.json()

    def get_pipeline(self, pipeline_id: str) -> Mapping[str, Any]:
        """Retrieves a specific pipeline by ID."""
        response = self._client.get(f'{self._base_url}/v1/configs/pipelines/{pipeline_id}')
        response.raise_for_status()
        return response.json()

    def create_pipeline(self, pipeline: Mapping[str, Any]) -> Mapping[str, Any]:
        """Creates a new pipeline configuration."""
        response = self._client.post(f'{self._base_url}/v1/configs/pipelines', json=pipeline)
        response.raise_for_status()
        return response.json()

    def update_pipeline(self, pipeline_id: str, pipeline: Mapping[str, Any]) -> Mapping[str, Any]:
        """Updates an existing pipeline configuration."""
        response = self._client.put(f'{self._base_url}/v1/configs/pipelines/{pipeline_id}', json=pipeline)
        response.raise_for_status()
        return response.json()

    def delete_pipeline(self, pipeline_id: str) -> None:
        """Deletes a pipeline configuration."""
        response = self._client.delete(f'{self._base_url}/v1/configs/pipelines/{pipeline_id}')
        response.raise_for_status()

    def start_evaluation(self, pipeline_id: str, dataset_id: str) -> 'Evaluation':
        """Starts a new evaluation job for a dataset using a pipeline."""
        response = self._client.post(
            f'{self._base_url}/v1/evaluations',
            json={'pipeline_id': pipeline_id, 'dataset_id': dataset_id},
        )
        response.raise_for_status()
        eval_id = response.json().get('evaluation_id')
        return Evaluation(
            evaluation_id=eval_id,
            client=self._client,
            base_url=self._base_url,
        )

    def evaluate_batch(self, pipeline_id: str, dataset_id: str) -> Mapping[str, Any]:
        """[DEPRECATED] Use start_evaluation() instead."""
        warnings.warn(
            'evaluate_batch is deprecated. Use start_evaluation() for client-driven iteration.',
            DeprecationWarning,
            stacklevel=2,
        )
        raise NotImplementedError(
            'evaluate_batch is deprecated. Please migrate to start_evaluation and manage the evaluation loop.'
        )


class AgentClient:
    """Client for Metric Helper Agent interaction."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip('/')

    def chat(self, messages: list[Mapping[str, Any]], metric_id: str | None = None) -> Mapping[str, Any]:
        """Sends chat conversation history to the Metric Helper Agent."""
        response = self._client.post(
            f'{self._base_url}/v1/agent/chat',
            json={'messages': list(messages), 'metric_id': metric_id}
        )
        response.raise_for_status()
        return response.json()

    def get_session(self, metric_id: str) -> Mapping[str, Any]:
        """Retrieves the persisted chat session history for a specific metric."""
        response = self._client.get(f'{self._base_url}/v1/agent/sessions/{metric_id}')
        response.raise_for_status()
        return response.json()

    def save_session(self, metric_id: str, messages: list[Mapping[str, Any]]) -> Mapping[str, Any]:
        """Explicitly saves or overwrites a chat session history for a metric."""
        response = self._client.post(
            f'{self._base_url}/v1/agent/sessions/{metric_id}',
            json={'messages': list(messages)}
        )
        response.raise_for_status()
        return response.json()

    def delete_session(self, metric_id: str) -> Mapping[str, Any]:
        """Clears the chat session history for a specific metric."""
        response = self._client.delete(f'{self._base_url}/v1/agent/sessions/{metric_id}')
        response.raise_for_status()
        return response.json()


class DocumentClient:
    """Client for managing documents in RAG knowledge base."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip('/')

    def upload_document(self, name: str, file_path: str, content_type: str = 'text/plain') -> Mapping[str, Any]:
        """Uploads a document file and embeds it synchronously."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'Document file not found: {file_path}')
        with open(file_path, 'rb') as f:
            files = {'file': (name, f, content_type)}
            response = self._client.post(f'{self._base_url}/v1/documents/upload', files=files)
            response.raise_for_status()
            return response.json()

    def list_documents(self) -> list[Mapping[str, Any]]:
        """Lists all uploaded documents stored in the database."""
        response = self._client.get(f'{self._base_url}/v1/documents')
        response.raise_for_status()
        return response.json()

    def delete_document(self, file_id: str) -> Mapping[str, Any]:
        """Removes a document and purges its vectors."""
        response = self._client.delete(f'{self._base_url}/v1/documents/{file_id}')
        response.raise_for_status()
        return response.json()


class Evaluation:
    """Represents a stateful evaluation job."""

    def __init__(self, evaluation_id: str, client: httpx.Client, base_url: str) -> None:
        """Initialize an Evaluation instance."""
        self.evaluation_id = evaluation_id
        self._client = client
        self._base_url = base_url
        self._active_cases: dict[str, 'CaseTracker'] = {}
        self._executor = ThreadPoolExecutor(thread_name_prefix=f'Eval-{evaluation_id}')

    def submit_testcase(
        self,
        testcase_id: str,
        runtime_ids: Sequence[RuntimeId],
        block: bool = False,
    ) -> Mapping[str, Any] | None:
        """Submits the execution telemetry for a specific test case to be evaluated."""
        if not block:
            def background_submit() -> None:
                try:
                    from .client import get_default_client
                    client = get_default_client()
                    if hasattr(client, 'flush'):
                        client.flush()
                    self.submit_testcase(testcase_id, runtime_ids, block=True)
                except Exception as e:
                    logger.warning('Failed to submit testcase %s: %s', testcase_id, str(e))

            self._executor.submit(background_submit)
            return None

        response = self._client.post(
            f'{self._base_url}/v1/evaluations/{self.evaluation_id}/testcases/{testcase_id}/submit',
            json={'runtime_ids': list(runtime_ids)},
        )
        response.raise_for_status()
        return response.json()

    def complete(self, block: bool = True) -> Mapping[str, Any] | None:
        """Marks the evaluation job as complete."""
        if not block:
            def background_complete() -> None:
                try:
                    self.complete(block=True)
                except Exception:
                    logger.warning('Failed to complete evaluation %s', self.evaluation_id)

            threading.Thread(target=background_complete, daemon=True).start()
            return None

        # Wait for all pending test case submissions before marking evaluation as complete.
        self._executor.shutdown(wait=True)

        response = self._client.post(
            f'{self._base_url}/v1/evaluations/{self.evaluation_id}/complete'
        )
        response.raise_for_status()
        return response.json()

    def get_status(self) -> Mapping[str, Any]:
        """Gets the overall batch run state and results."""
        response = self._client.get(f'{self._base_url}/v1/evaluations/{self.evaluation_id}')
        response.raise_for_status()
        return response.json()

    def get_summary(self) -> Mapping[str, Any]:
        """Gets the evaluation summary metrics."""
        response = self._client.get(f'{self._base_url}/v1/evaluations/{self.evaluation_id}/summary')
        response.raise_for_status()
        return response.json()

    def get_testcase_result(self, testcase_id: str) -> Mapping[str, Any]:
        """Gets the result of a specific testcase."""
        response = self._client.get(f'{self._base_url}/v1/evaluations/{self.evaluation_id}/testcases/{testcase_id}')
        response.raise_for_status()
        return response.json()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.complete(block=False)

    def start_case(self, testcase_id: str) -> 'CaseTracker':
        """Starts tracking a test case explicitly without a context manager."""
        tracker = CaseTracker(testcase_id, self)
        self._active_cases[testcase_id] = tracker
        return tracker

    def complete_case(self, testcase_id: str) -> None:
        """Completes tracking a test case and submits it in the background."""
        tracker = self._active_cases.pop(testcase_id, None)
        if tracker and tracker.runtimes:
            self.submit_testcase(testcase_id, tracker.runtimes, block=False)

    @contextmanager
    def track_case(self, testcase_id: str) -> Generator['CaseTracker', None, None]:
        """Context manager that yields a CaseTracker and submits the testcase on exit."""
        tracker = self.start_case(testcase_id)
        token = current_evaluation_runtimes.set(tracker.runtimes)
        try:
            yield tracker
        finally:
            current_evaluation_runtimes.reset(token)
            self.complete_case(testcase_id)


class CaseTracker:
    """Explicit tracker for a test case."""

    def __init__(self, testcase_id: str, evaluation: Evaluation) -> None:
        """Initialize the CaseTracker."""
        self.testcase_id = testcase_id
        self.evaluation = evaluation
        self.runtimes: list[RuntimeId] = []

    def add_runtime(self, runtime_id: RuntimeId) -> None:
        """Add a runtime ID to this test case."""
        self.runtimes.append(runtime_id)

    def complete(self) -> None:
        """Complete the test case and submit runtimes."""
        self.evaluation.complete_case(self.testcase_id)

