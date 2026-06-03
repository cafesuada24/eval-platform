import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.management import DatasetClient, PipelineClient
from httpx import Response


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.Client") as mock_client:
        yield mock_client


def test_eval_client_initializes_management_clients(mock_httpx_client):
    client = EvalClient(api_key="test_key", base_url="http://test")
    assert hasattr(client, "datasets")
    assert isinstance(client.datasets, DatasetClient)
    assert hasattr(client, "pipelines")
    assert isinstance(client.pipelines, PipelineClient)


def test_dataset_upload_json():
    mock_client = Mock()
    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"id": "123", "name": "test_dataset"}
    mock_client.post.return_value = mock_response

    dataset_client = DatasetClient(client=mock_client, base_url="http://test")

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump([{"input": "hello"}], f)
        temp_path = f.name

    try:
        result = dataset_client.upload_json("test_dataset", temp_path)

        assert result == {"id": "123", "name": "test_dataset"}
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://test/v1/datasets/"
        assert "files" in kwargs
        assert "file" in kwargs["files"]
    finally:
        os.unlink(temp_path)


def test_dataset_upload_csv():
    mock_client = Mock()
    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"id": "124", "name": "test_csv"}
    mock_client.post.return_value = mock_response

    dataset_client = DatasetClient(client=mock_client, base_url="http://test")

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        f.write("input\nhello\n")
        temp_path = f.name

    try:
        result = dataset_client.upload_csv("test_csv", temp_path)

        assert result == {"id": "124", "name": "test_csv"}
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://test/v1/datasets/"
        assert "files" in kwargs
    finally:
        os.unlink(temp_path)


def test_pipeline_evaluate_batch():
    mock_client = Mock()
    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"job_id": "job123", "status": "PENDING"}
    mock_client.post.return_value = mock_response

    pipeline_client = PipelineClient(client=mock_client, base_url="http://test")
    result = pipeline_client.evaluate_batch("pipeline_1", "dataset_1")

    assert result == {"job_id": "job123", "status": "PENDING"}
    mock_client.post.assert_called_once_with(
        "http://test/v1/configs/pipelines/pipeline_1/run_batch",
        json={"dataset_id": "dataset_1"}
    )
