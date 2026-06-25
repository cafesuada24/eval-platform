"""Integration tests for MM-Vet multimodal dataset ingestion."""

import shutil
from typing import Any

import httpx
from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

MOCK_MM_VET_METADATA = {
    'v1_1': {
        'imagename': 'v1_1.jpg',
        'question': 'Identify the primary colors in the image.',
        'answer': 'Red, green, blue',
        'capability': ['recognition'],
    },
    'v1_2': {
        'imagename': 'v1_2.jpg',
        'question': 'What number is displayed?',
        'answer': '42',
        'capability': ['OCR'],
    },
    'v1_3': {
        'imagename': 'v1_3.jpg',
        'question': 'Solve the equation in the picture.',
        'answer': 'x = 5',
        'capability': ['math'],
    },
}

# 1x1 pixel dummy JPEG bytes
MOCK_IMAGE_BYTES = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\xff\xd9'


def _get_mm_vet_metadata() -> dict[str, Any]:
    """Fetch MM-Vet metadata with network fallback."""
    url = 'https://raw.githubusercontent.com/yuweihao/MM-Vet_data/main/mm-vet.json'
    try:
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except httpx.HTTPError:
        pass
    return MOCK_MM_VET_METADATA


def _get_image_bytes(imagename: str) -> bytes:
    """Fetch image bytes with network fallback."""
    url = f'https://raw.githubusercontent.com/yuweihao/MM-Vet_data/main/images/{imagename}'
    try:
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 200:
            return response.content
    except httpx.HTTPError:
        pass
    return MOCK_IMAGE_BYTES


def test_mm_vet_ingestion_integration() -> None:
    """Verify end-to-end MM-Vet dataset ingestion flow, mapping, and teardown."""
    mm_vet_data = _get_mm_vet_metadata()
    target_keys = list(mm_vet_data.keys())[:3]

    dataset_id: str | None = None
    try:
        # Create the dataset in backend
        create_response = client.post(
            '/v1/datasets/',
            json={
                'name': 'MM-Vet-Benchmark-Sample',
                'schema': {'inputs': {}, 'outputs': {}},
            },
        )
        assert create_response.status_code == 201
        dataset_info = create_response.json()
        dataset_id = dataset_info['id']

        uploaded_files: dict[str, str] = {}
        # Download images and upload to API
        for key in target_keys:
            imagename = mm_vet_data[key]['imagename']
            image_bytes = _get_image_bytes(imagename)

            # Upload file via endpoint
            files_payload = {'file': (imagename, image_bytes, 'image/jpeg')}
            file_response = client.post(
                f'/v1/datasets/{dataset_id}/files',
                files=files_payload,
            )
            assert file_response.status_code == 201
            file_info = file_response.json()
            uploaded_files[imagename] = file_info['file_id']

        # Map and add Test Cases
        for key in target_keys:
            case_raw = mm_vet_data[key]
            imagename = case_raw['imagename']
            file_id = uploaded_files[imagename]

            case_payload = {
                'inputs': {'query': case_raw['question'], 'image_id': file_id},
                'expected_outputs': {'expected_output': case_raw['answer']},
                'metadata': {
                    'mm_vet_id': key,
                    'capability': case_raw.get('capability', []),
                },
            }
            case_response = client.post(
                f'/v1/datasets/{dataset_id}/cases',
                json=case_payload,
            )
            assert case_response.status_code == 201

        # Verify dataset contents and files on disk
        get_response = client.get(f'/v1/datasets/{dataset_id}')
        assert get_response.status_code == 200
        retrieved_dataset = get_response.json()
        assert len(retrieved_dataset['cases']) == 3

        # Verify first case content matches source metadata
        first_case = retrieved_dataset['cases'][0]
        first_key = target_keys[0]
        first_source = mm_vet_data[first_key]
        assert first_case['inputs']['query'] == first_source['question']
        assert (
            first_case['expected_outputs']['expected_output']
            == first_source['answer']
        )
        assert first_case['metadata']['mm_vet_id'] == first_key

        # Verify files exist in settings.dataset_files_dir / dataset_id
        dataset_files_dir = settings.dataset_files_dir / dataset_id
        assert dataset_files_dir.exists()
        for file_id in uploaded_files.values():
            physical_file = dataset_files_dir / file_id
            assert physical_file.exists()

    finally:
        if dataset_id is not None:
            # Cleanup after test completion
            # Delete dataset file
            dataset_json_path = settings.datasets_dir / f'{dataset_id}.json'
            if dataset_json_path.exists():
                dataset_json_path.unlink()

            # Delete uploaded files directory
            dataset_files_dir = settings.dataset_files_dir / dataset_id
            if dataset_files_dir.exists():
                shutil.rmtree(dataset_files_dir)


