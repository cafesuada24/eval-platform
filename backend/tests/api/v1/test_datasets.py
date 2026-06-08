"""Tests for datasets endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_json_dataset():
    json_content = '[{"inputs": {"query": "hello"}, "outputs": {"expected_output": "world"}}]'
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("test.json", json_content.encode("utf-8"), "application/json")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test.json"
    assert len(data["cases"]) == 1
    assert data["cases"][0]["inputs"]["query"] == "hello"


def test_upload_flat_json_dataset():
    json_content = '[{"query": "flat_hello", "expected_output": "flat_world", "image_id": "123"}]'
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("test_flat.json", json_content.encode("utf-8"), "application/json")},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["cases"]) == 1
    assert data["cases"][0]["inputs"]["query"] == "flat_hello"
    assert data["cases"][0]["inputs"]["image_id"] == "123"
    assert data["cases"][0]["expected_outputs"]["expected_output"] == "flat_world"


def test_upload_csv_dataset():
    csv_content = "query,expected_output\nhello,world"
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test.csv"
    assert len(data["cases"]) == 1
    assert data["cases"][0]["inputs"]["query"] == "hello"


def test_get_dataset_by_id():
    json_content = '[{"inputs": {"query": "get_test"}, "outputs": {"expected_output": "result"}}]'
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("get_test.json", json_content.encode("utf-8"), "application/json")},
    )
    assert response.status_code == 201
    dataset_id = response.json()["id"]

    response2 = client.get(f"/v1/datasets/{dataset_id}")
    assert response2.status_code == 200
    assert response2.json()["id"] == dataset_id
    assert response2.json()["name"] == "get_test.json"

def test_get_dataset_by_id_not_found():
    random_id = str(uuid4())
    response = client.get(f"/v1/datasets/{random_id}")
    assert response.status_code == 404

def test_dataset_file_upload_and_retrieve():
    # 1. Create a dataset
    dataset_response = client.post("/v1/datasets/", json={"name": "Test Files Dataset", "schema": {"inputs": {}, "outputs": {}}})
    dataset_id = dataset_response.json()["id"]

    # 2. Upload a fake image file
    file_content = b"fake image bytes"
    upload_response = client.post(
        f"/v1/datasets/{dataset_id}/files",
        files={"file": ("test_image.png", file_content, "image/png")}
    )
    assert upload_response.status_code == 201
    file_data = upload_response.json()
    assert file_data["filename"] == "test_image.png"
    
    file_id = file_data["file_id"]
    
    # 3. Retrieve the image file
    get_response = client.get(f"/v1/datasets/{dataset_id}/files/{file_id}")
    assert get_response.status_code == 200
    assert get_response.content == file_content
    assert "image/png" in get_response.headers.get("content-type", "")


def test_upload_jsonl_dataset():
    jsonl_content = '{"inputs": {"query": "hello_jsonl"}, "outputs": {"expected_output": "world_jsonl"}}\n{"inputs": {"query": "hello_jsonl2"}, "outputs": {"expected_output": "world_jsonl2"}}'
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("test.jsonl", jsonl_content.encode("utf-8"), "application/jsonl")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test.jsonl"
    assert len(data["cases"]) == 2
    assert data["cases"][0]["inputs"]["query"] == "hello_jsonl"
    assert data["cases"][1]["inputs"]["query"] == "hello_jsonl2"


def test_upload_with_column_mapping():
    csv_content = "prompt,response,tag\nhello_csv,world_csv,testing"
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("test_map.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"column_mapping": '{"prompt": "query", "response": "expected_output", "tag": "metadata.category"}'}
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["cases"]) == 1
    assert data["cases"][0]["inputs"]["query"] == "hello_csv"
    assert data["cases"][0]["expected_outputs"]["expected_output"] == "world_csv"
    assert data["cases"][0]["metadata"]["category"] == "testing"


def test_upload_with_column_mapping_missing_query():
    csv_content = "prompt,response\nhello_csv,world_csv"
    response = client.post(
        "/v1/datasets/upload",
        files={"file": ("test_map_fail.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"column_mapping": '{"response": "expected_output"}'}
    )
    assert response.status_code == 400


def test_create_metric_without_id():
    metric_data = {
        "name": "Test Metric DTO",
        "description": "Metric created via DTO",
        "type": "primitive",
        "required_inputs": ["query", "response"],
        "scoring_scale": {"min": 0, "max": 5, "data_type": "integer"},
        "formula": "1"
    }
    response = client.post("/v1/configs/metrics", json=metric_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Metric DTO"
    assert "id" in data

    # Clean up
    client.delete(f"/v1/configs/metrics/{data['id']}")


def test_patch_dataset_partial():
    # Create dataset
    dataset_response = client.post(
        "/v1/datasets/",
        json={"name": "Original Name", "schema": {"inputs": {}, "outputs": {}}}
    )
    dataset_id = dataset_response.json()["id"]

    # Partial update name only
    patch_response = client.patch(
        f"/v1/datasets/{dataset_id}",
        json={"name": "Updated Name"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Updated Name"
    # Description should stay None (or not change if it was set)
    assert patch_response.json()["description"] is None

    # Partial update description only
    patch_response2 = client.patch(
        f"/v1/datasets/{dataset_id}",
        json={"description": "Updated Description"}
    )
    assert patch_response2.status_code == 200
    assert patch_response2.json()["name"] == "Updated Name"
    assert patch_response2.json()["description"] == "Updated Description"


def test_delete_endpoints_204():
    # Ingest a runtime
    runtime_data = {
        "runtime_id": str(uuid4()),
        "events": [],
        "usage": {"cpu_percent": 0, "memory_bytes": 0}
    }
    put_response = client.put("/v1/runtimes", json=runtime_data)
    assert put_response.status_code == 200
    runtime_id = put_response.json()["runtime_id"]

    # Delete runtime should return 204
    delete_response = client.delete(f"/v1/runtimes/{runtime_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""

