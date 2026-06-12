"""Integration tests for MM-Vet multimodal dataset ingestion."""

import shutil
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

MOCK_MM_VET_METADATA = {
    'v1_1': {
        'imagename': 'v1_1.jpg',
        'question': 'Identify the primary colors in the image.',
        'answer': 'Red, green, blue',
        'capability': ['recognition']
    },
    'v1_2': {
        'imagename': 'v1_2.jpg',
        'question': 'What number is displayed?',
        'answer': '42',
        'capability': ['OCR']
    },
    'v1_3': {
        'imagename': 'v1_3.jpg',
        'question': 'Solve the equation in the picture.',
        'answer': 'x = 5',
        'capability': ['math']
    }
}

# 1x1 pixel dummy JPEG bytes
MOCK_IMAGE_BYTES = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\xff\xd9'


def test_mm_vet_ingestion_integration() -> None:
    """Verify end-to-end MM-Vet dataset ingestion flow, mapping, and teardown."""
    # 1. Download metadata with network fallback
    mm_vet_url = 'https://raw.githubusercontent.com/yuweihao/MM-Vet_data/main/mm-vet.json'
    mm_vet_data = {}
    try:
        response = httpx.get(mm_vet_url, timeout=5.0)
        if response.status_code == 200:
            mm_vet_data = response.json()
    except Exception:
        pass

    # Fallback to mock data if download failed or empty
    if not mm_vet_data:
        mm_vet_data = MOCK_MM_VET_METADATA

    # Slice the first 3 keys for testing
    target_keys = list(mm_vet_data.keys())[:3]

    dataset_id = None
    try:
        # 2. Create the dataset in backend
        create_response = client.post(
            '/v1/datasets/',
            json={'name': 'MM-Vet-Benchmark-Sample', 'schema': {'inputs': {}, 'outputs': {}}}
        )
        assert create_response.status_code == 201
        dataset_info = create_response.json()
        dataset_id = dataset_info['id']

        uploaded_files = {}
        # 3. Download images and upload to API
        for key in target_keys:
            imagename = mm_vet_data[key]['imagename']
            img_url = f'https://raw.githubusercontent.com/yuweihao/MM-Vet_data/main/images/{imagename}'

            image_bytes = None
            try:
                img_response = httpx.get(img_url, timeout=5.0)
                if img_response.status_code == 200:
                    image_bytes = img_response.content
            except Exception:
                pass

            if not image_bytes:
                image_bytes = MOCK_IMAGE_BYTES

            # Upload file via endpoint
            files_payload = {'file': (imagename, image_bytes, 'image/jpeg')}
            file_response = client.post(
                f'/v1/datasets/{dataset_id}/files',
                files=files_payload
            )
            assert file_response.status_code == 201
            file_info = file_response.json()
            uploaded_files[imagename] = file_info['file_id']

        # 4. Map and add Test Cases
        for key in target_keys:
            case_raw = mm_vet_data[key]
            imagename = case_raw['imagename']
            file_id = uploaded_files[imagename]

            case_payload = {
                'inputs': {
                    'query': case_raw['question'],
                    'image_id': file_id
                },
                'expected_outputs': {
                    'expected_output': case_raw['answer']
                },
                'metadata': {
                    'mm_vet_id': key,
                    'capability': case_raw.get('capability', [])
                }
            }
            case_response = client.post(
                f'/v1/datasets/{dataset_id}/cases',
                json=case_payload
            )
            assert case_response.status_code == 201

        # 5. Verify dataset contents and files on disk
        get_response = client.get(f'/v1/datasets/{dataset_id}')
        assert get_response.status_code == 200
        retrieved_dataset = get_response.json()
        assert len(retrieved_dataset['cases']) == 3

        # Verify first case content matches source metadata
        first_case = retrieved_dataset['cases'][0]
        first_key = target_keys[0]
        first_source = mm_vet_data[first_key]
        assert first_case['inputs']['query'] == first_source['question']
        assert first_case['expected_outputs']['expected_output'] == first_source['answer']
        assert first_case['metadata']['mm_vet_id'] == first_key

        # Verify files exist in settings.dataset_files_dir / dataset_id
        dataset_files_dir = settings.dataset_files_dir / dataset_id
        assert dataset_files_dir.exists()
        for imagename, file_id in uploaded_files.items():
            physical_file = dataset_files_dir / file_id
            assert physical_file.exists()

    finally:
        if dataset_id is not None:
            # 6. Cleanup after test completion
            # Delete dataset file
            dataset_json_path = settings.datasets_dir / f'{dataset_id}.json'
            if dataset_json_path.exists():
                dataset_json_path.unlink()

            # Delete uploaded files directory
            dataset_files_dir = settings.dataset_files_dir / dataset_id
            if dataset_files_dir.exists():
                shutil.rmtree(dataset_files_dir)
