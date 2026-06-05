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
