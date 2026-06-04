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


class DatasetClient:
    """Client for managing datasets."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        """Initialize the DatasetClient.

        Args:
            client: The HTTP client to use for requests.
            base_url: The base URL of the EvalPlatform API.
        """
        self._client = client
        self._base_url = base_url.rstrip('/')

    def upload_json(self, name: str, file_path: str) -> Mapping[str, Any]:
        """Uploads a JSON dataset.

        Args:
            name: The name of the dataset.
            file_path: The path to the JSON file.

        Returns:
            The API response JSON.
        """
        return self._upload_file(name, file_path, 'application/json')

    def upload_csv(self, name: str, file_path: str) -> Mapping[str, Any]:
        """Uploads a CSV dataset.

        Args:
            name: The name of the dataset.
            file_path: The path to the CSV file.

        Returns:
            The API response JSON.
        """
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
            response = self._client.post(f'{self._base_url}/v1/datasets/', files=files)
            response.raise_for_status()
            return response.json()

    def get_cases(self, dataset_id: str) -> list[Mapping[str, Any]]:
        """Retrieves test cases for a given dataset."""
        response = self._client.get(f'{self._base_url}/v1/datasets/{dataset_id}')
        response.raise_for_status()
        data = response.json()
        return data.get('cases', [])


class Evaluation:
    """Represents a stateful evaluation job."""

    def __init__(self, evaluation_id: str, client: httpx.Client, base_url: str) -> None:
        """Initialize an Evaluation instance.

        Args:
            evaluation_id: The unique ID of the evaluation job.
            client: The HTTP client for API requests.
            base_url: The base URL of the EvalPlatform API.
        """
        self.evaluation_id = evaluation_id
        self._client = client
        self._base_url = base_url
        self._active_cases: dict[str, 'CaseTracker'] = {}
        # Single responsibility: use a dedicated thread pool for non-blocking submissions.
        self._executor = ThreadPoolExecutor(thread_name_prefix=f'Eval-{evaluation_id}')

    def submit_testcase(
        self,
        testcase_id: str,
        runtime_ids: Sequence[RuntimeId],
        block: bool = False,
    ) -> Mapping[str, Any] | None:
        """Submits the execution telemetry for a specific test case to be evaluated.

        Args:
            testcase_id: The ID of the testcase.
            runtime_ids: The sequence of runtime trace IDs.
            block: If True, blocks until the submission completes.
                   If False, sends the request in the background.
        """
        if not block:

            def background_submit() -> None:
                try:
                    from .client import get_default_client

                    client = get_default_client()
                    if hasattr(client, 'flush'):
                        client.flush()
                    self.submit_testcase(testcase_id, runtime_ids, block=True)
                except Exception:
                    logger.warning('Failed to submit testcase %s', testcase_id)

            self._executor.submit(background_submit)
            return None

        response = self._client.post(
            f'{self._base_url}/v1/evaluations/{self.evaluation_id}/testcases/{testcase_id}/submit',
            json={'runtime_ids': list(runtime_ids)},
        )
        response.raise_for_status()
        return response.json()

    def complete(self, block: bool = True) -> Mapping[str, Any] | None:
        """Marks the evaluation job as complete.

        Args:
            block: If True, blocks until the completion request finishes.
                   If False, sends the request in the background.
        """
        if not block:

            def background_complete() -> None:
                try:
                    self.complete(block=True)
                except Exception:
                    logger.warning(
                        'Failed to complete evaluation %s', self.evaluation_id
                    )

            threading.Thread(target=background_complete, daemon=True).start()
            return None

        # Fix hidden bug: Wait for all pending test case submissions before marking evaluation as complete.
        self._executor.shutdown(wait=True)

        response = self._client.post(
            f'{self._base_url}/v1/evaluations/{self.evaluation_id}/complete'
        )
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
        try:
            yield tracker
        finally:
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


class PipelineClient:
    """Client for managing pipelines and batch evaluation."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        """Initialize the PipelineClient.

        Args:
            client: The HTTP client for API requests.
            base_url: The base URL of the EvalPlatform API.
        """
        self._client = client
        self._base_url = base_url.rstrip('/')

    def start_evaluation(self, pipeline_id: str, dataset_id: str) -> Evaluation:
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
