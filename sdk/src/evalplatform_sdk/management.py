import os
from typing import Any

import httpx


class DatasetClient:
    """Client for managing datasets."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def upload_json(self, name: str, file_path: str) -> dict[str, Any]:
        """Uploads a JSON dataset."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(file_path, "rb") as f:
            files = {"file": (name, f, "application/json")}
            response = self._client.post(f"{self._base_url}/v1/datasets/", files=files)
            response.raise_for_status()
            return response.json()

    def upload_csv(self, name: str, file_path: str) -> dict[str, Any]:
        """Uploads a CSV dataset."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(file_path, "rb") as f:
            files = {"file": (name, f, "text/csv")}
            response = self._client.post(f"{self._base_url}/v1/datasets/", files=files)
            response.raise_for_status()
            return response.json()


class PipelineClient:
    """Client for managing pipelines and batch evaluation."""

    def __init__(self, client: httpx.Client, base_url: str):
        self._client = client
        self._base_url = base_url.rstrip("/")

    def evaluate_batch(self, pipeline_id: str, dataset_id: str) -> dict[str, Any]:
        """Triggers a batch evaluation job for a pipeline against a dataset."""
        response = self._client.post(
            f"{self._base_url}/v1/configs/pipelines/{pipeline_id}/run_batch",
            json={"dataset_id": dataset_id},
        )
        response.raise_for_status()
        return response.json()
