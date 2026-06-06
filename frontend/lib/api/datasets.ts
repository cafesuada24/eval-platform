import { Dataset, TestCase, PaginatedTestCases, FileAsset } from "@/types/dataset";

const BASE_URL = "http://localhost:8000/v1/datasets";

export async function fetchDataset(id: string): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/${id}`);
  if (!res.ok) throw new Error("Failed to fetch dataset");
  return res.json();
}

export async function createDataset(name: string, schema: Dataset["schema"]): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, schema }),
  });
  if (!res.ok) throw new Error("Failed to create dataset");
  return res.json();
}

export async function updateDataset(id: string, name: string, schema: Dataset["schema"]): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, schema }),
  });
  if (!res.ok) throw new Error("Failed to update dataset");
  return res.json();
}

export async function fetchTestCases(datasetId: string, page = 1, limit = 50): Promise<PaginatedTestCases> {
  const res = await fetch(`${BASE_URL}/${datasetId}/cases?page=${page}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch test cases");
  const data = await res.json();
  // Backend returns a flat array of TestCase[], so we wrap it into PaginatedTestCases
  if (Array.isArray(data)) {
    const totalCountHeader = res.headers.get("x-total-count");
    return {
      items: data,
      total: totalCountHeader ? parseInt(totalCountHeader, 10) : (data.length === limit ? page * limit + 1 : (page - 1) * limit + data.length),
      page,
      limit
    };
  }
  return data;
}

export async function createTestCase(datasetId: string, data: Omit<TestCase, "id">): Promise<TestCase> {
  const res = await fetch(`${BASE_URL}/${datasetId}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create test case");
  return res.json();
}

export async function updateTestCase(datasetId: string, caseId: string, data: Omit<TestCase, "id">): Promise<TestCase> {
  const res = await fetch(`${BASE_URL}/${datasetId}/cases/${caseId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update test case");
  return res.json();
}

export async function deleteTestCase(datasetId: string, caseId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/${datasetId}/cases/${caseId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete test case");
}

export async function uploadFile(datasetId: string, file: File): Promise<FileAsset> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/${datasetId}/files`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) throw new Error("Failed to upload file");
  return res.json();
}

export async function fetchDocuments(): Promise<FileAsset[]> {
  // Using the absolute API base URL for generic documents
  const API_BASE_URL = "http://localhost:8000/v1/documents";
  const res = await fetch(API_BASE_URL);
  if (!res.ok) throw new Error("Failed to fetch documents");
  const data = await res.json();
  return data.map((d: any) => ({
    file_id: d.id,
    filename: d.name,
    url: ""
  }));
}

export async function fetchDatasetFiles(datasetId: string): Promise<FileAsset[]> {
  const res = await fetch(`${BASE_URL}/${datasetId}/files`);
  if (!res.ok) throw new Error("Failed to fetch dataset files");
  return res.json();
}
