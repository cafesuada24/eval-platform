"""Script to download the Paul Graham Essay dataset and map it for benchmarking."""

import json
import os
import urllib.request


def download_dataset():
    data_dir = "benchmark_data"
    os.makedirs(data_dir, exist_ok=True)

    # 1. Download source text
    print("Downloading Paul Graham essay source text...")
    source_url = "https://media.githubusercontent.com/media/run-llama/llama-datasets/main/llama_datasets/paul_graham_essay/source_files/source.txt"
    req_txt = urllib.request.Request(
        source_url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req_txt) as r:
        text_content = r.read().decode("utf-8")

    # Save as paul_graham_essay.txt
    essay_path = os.path.join(data_dir, "paul_graham_essay.txt")
    with open(essay_path, "w", encoding="utf-8") as f:
        f.write(text_content)

    # 2. Download LlamaDataset JSON (LFS)
    print("Downloading LlamaDataset QA pairs...")
    json_url = "https://media.githubusercontent.com/media/run-llama/llama-datasets/main/llama_datasets/paul_graham_essay/rag_dataset.json"
    req_json = urllib.request.Request(
        json_url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req_json) as r:
        dataset_data = json.loads(r.read())

    # 3. Map examples to benchmark format
    examples = dataset_data.get("examples", [])
    mapped_cases = []
    for i, ex in enumerate(examples):
        mapped_cases.append({
            "id": f"TC_{i+1:03d}",
            "query": ex["query"],
            "expected_sources": ["paul_graham_essay.txt"],
            "expected_content_types": ["text"],
            "reference_answer": ex["reference_answer"],
            "category": "paul_graham_essay",
        })

    # 4. Save to test_cases.json (first 5 by default to prevent API rate limit exhaustion)
    cases_path = os.path.join(data_dir, "test_cases.json")
    with open(cases_path, "w", encoding="utf-8") as f:
        json.dump(mapped_cases[:5], f, indent=2)

    # Save full set to test_cases_full.json
    cases_full_path = os.path.join(data_dir, "test_cases_full.json")
    with open(cases_full_path, "w", encoding="utf-8") as f:
        json.dump(mapped_cases, f, indent=2)

    # 5. Clean up old dummy files to prevent polluting the index
    old_files = ["sample_text.txt", "sample_doc.pdf", "sample_image.png"]
    for old_file in old_files:
        path = os.path.join(data_dir, old_file)
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed old dummy file: {old_file}")

    print(
        f"\nSuccessfully downloaded Paul Graham essay and generated {len(mapped_cases)} test cases."
    )
    print(
        "-> Saved first 5 cases to benchmark_data/test_cases.json (Run time: ~1 minute)."
    )
    print("-> Saved full 44 cases to benchmark_data/test_cases_full.json.")


if __name__ == "__main__":
    download_dataset()
