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
        assert args[0] == "http://test/v1/datasets/upload"
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
        assert args[0] == "http://test/v1/datasets/upload"
        assert "files" in kwargs
    finally:
        os.unlink(temp_path)


def test_pipeline_start_evaluation():
    mock_client = Mock()
    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"evaluation_id": "eval123"}
    mock_client.post.return_value = mock_response

    pipeline_client = PipelineClient(client=mock_client, base_url="http://test")
    eval_job = pipeline_client.start_evaluation("pipeline_1", "dataset_1")

    assert eval_job.evaluation_id == "eval123"
    mock_client.post.assert_called_once_with(
        "http://test/v1/evaluations",
        json={"pipeline_id": "pipeline_1", "dataset_id": "dataset_1"}
    )


def test_evaluation_context_manager():
    mock_client = Mock()
    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"status": "completed"}
    mock_client.post.return_value = mock_response

    from evalplatform_sdk.management import Evaluation
    eval_job = Evaluation(evaluation_id="eval123", client=mock_client, base_url="http://test")
    
    with eval_job as e:
        assert e is eval_job
        
    mock_client.post.assert_called_once_with(
        "http://test/v1/evaluations/eval123/complete"
    )

@patch("evalplatform_sdk.client.get_default_client")
def test_evaluation_track_case(mock_get_client):
    mock_client = Mock()
    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"status": "success"}
    mock_client.post.return_value = mock_response
    
    mock_eval_client = Mock()
    mock_get_client.return_value = mock_eval_client

    from evalplatform_sdk.management import Evaluation, current_evaluation_runtimes
    eval_job = Evaluation(evaluation_id="eval123", client=mock_client, base_url="http://test")
    
    with eval_job.track_case("testcase_1"):
        runtimes = current_evaluation_runtimes.get()
        assert runtimes == []
        runtimes.append("runtime123")
        
    mock_client.post.assert_called_once_with(
        "http://test/v1/evaluations/eval123/testcases/testcase_1/submit",
        json={"runtime_ids": ["runtime123"]}
    )
    mock_eval_client.flush.assert_called_once()
