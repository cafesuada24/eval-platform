import requests
import uuid

url = "http://127.0.0.1:8000/v1"

# 1. Ingest events
trace_id = str(uuid.uuid4())
events = [
    {
        "runtime_id": trace_id,
        "event_type": "generation.start",
        "payload": {"prompt": "Hello"}
    },
    {
        "runtime_id": trace_id,
        "event_type": "generation.end",
        "payload": {"response": "Hi there"}
    }
]

print("Ingesting...")
resp = requests.post(f"{url}/events", json=events)
print(resp.status_code, resp.json())

# Wait a tiny bit for background task
import time
time.sleep(1)

# 2. Get runtimes
print("Fetching runtimes...")
resp = requests.get(f"{url}/runtimes")
print(resp.status_code, resp.json())

# 3. Get specific runtime
print("Fetching specific runtime...")
resp = requests.get(f"{url}/runtimes/{trace_id}")
print(resp.status_code, resp.json())

# 4. Delete runtime
print("Deleting runtime...")
resp = requests.delete(f"{url}/runtimes/{trace_id}")
print(resp.status_code, resp.json())

