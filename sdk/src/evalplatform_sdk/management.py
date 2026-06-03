import contextvars
import os
import warnings
from contextlib import contextmanager
from typing import Any

import httpx

from .client import get_default_client

current_evaluation_runtimes = contextvars.ContextVar(
    'current_evaluation_runtimes',
    default=None,
)


class DatasetClient:
    """Client for managing datasets."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip('/')

    def upload_json(self, name: str, file_path: str) -> dict[str, Any]:
        """Uploads a JSON dataset."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'Dataset file not found: {file_path}')

        with open(file_path, 'rb') as f:
            files = {'file': (name, f, 'application/json')}
            response = self._client.post(f'{self._base_url}/v1/datasets/', files=files)
            response.raise_for_status()
            return response.json()

    def upload_csv(self, name: str, file_path: str) -> dict[str, Any]:
        """Uploads a CSV dataset."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'Dataset file not found: {file_path}')

        with open(file_path, 'rb') as f:
            files = {'file': (name, f, 'text/csv')}
            response = self._client.post(f'{self._base_url}/v1/datasets/', files=files)
            response.raise_for_status()
            return response.json()

    def get_cases(self, dataset_id: str) -> list[dict[str, Any]]:
        """Retrieves test cases for a given dataset."""
        response = self._client.get(f'{self._base_url}/v1/datasets/{dataset_id}')
        response.raise_for_status()
        data = response.json()
        return data.get('cases', [])


class Evaluation:
    """Represents a stateful evaluation job."""

    def __init__(self, evaluation_id: str, client: httpx.Client, base_url: str):
        self.evaluation_id = evaluation_id
        self._client = client
        self._base_url = base_url

    def submit_testcase(
        self,
        testcase_id: str,
        runtime_ids: list[str],
    ) -> dict[str, Any]:
        """Submits the execution telemetry for a specific test case to be evaluated."""
        response = self._client.post(
            f'{self._base_url}/v1/evaluations/{self.evaluation_id}/testcases/{testcase_id}/submit',
            json={'runtime_ids': runtime_ids},
        )
        response.raise_for_status()
        return response.json()

    def complete(self) -> dict[str, Any]:
        """Marks the evaluation job as complete."""
        response = self._client.post(
            f'{self._base_url}/v1/evaluations/{self.evaluation_id}/complete'
        )
        response.raise_for_status()
        return response.json()

    def __enter__(self) -> 'Evaluation':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        import threading
        def background_complete():
            try:
                self.complete()
            except Exception:
                import logging
                logging.getLogger(__name__).warning("Failed to complete evaluation %s", self.evaluation_id)
        threading.Thread(target=background_complete, daemon=True).start()

    @contextmanager
    def track_case(self, testcase_id: str):
        """Context manager that automatically tracks generated trace_ids and submits the testcase."""
        runtimes = []
        token = current_evaluation_runtimes.set(runtimes)
        try:
            yield
        finally:
            current_evaluation_runtimes.reset(token)

            if runtimes:
                import threading
                def background_submit():
                    try:
                        client = get_default_client()
                        if hasattr(client, 'flush'):
                            client.flush()
                        self.submit_testcase(testcase_id, runtimes)
                    except Exception:
                        import logging
                        logging.getLogger(__name__).warning("Failed to submit testcase %s", testcase_id)
                        
                threading.Thread(target=background_submit, daemon=True).start()


class PipelineClient:
    """Client for managing pipelines and batch evaluation."""

    def __init__(self, client: httpx.Client, base_url: str):
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
            evaluation_id=eval_id, client=self._client, base_url=self._base_url
        )

    def evaluate_batch(self, pipeline_id: str, dataset_id: str) -> dict[str, Any]:
        """[DEPRECATED] Use start_evaluation() instead."""

        warnings.warn(
            'evaluate_batch is deprecated. Use start_evaluation() for client-driven iteration.',
            DeprecationWarning,
        )

        # We can still provide a thin wrapper just in case.
        # But this method requires the client to run things now.
        raise NotImplementedError(
            'evaluate_batch is deprecated. Please migrate to start_evaluation and manage the evaluation loop.'
        )
