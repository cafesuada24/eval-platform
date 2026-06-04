"""Tests for datasets endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_json_dataset():
    json_content = '[{"input_text": "hello", "expected_output": "world"}]'
    response = client.post(
        "/v1/datasets/",
        files={"file": ("test.json", json_content.encode("utf-8"), "application/json")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test.json"
    assert len(data["cases"]) == 1
    assert data["cases"][0]["input_text"] == "hello"


def test_upload_csv_dataset():
    csv_content = "input_text,expected_output\nhello,world"
    response = client.post(
        "/v1/datasets/",
        files={"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test.csv"
    assert len(data["cases"]) == 1
    assert data["cases"][0]["input_text"] == "hello"


def test_get_dataset_by_id():
    json_content = '[{"input_text": "get_test", "expected_output": "result"}]'
    response = client.post(
        "/v1/datasets/",
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
