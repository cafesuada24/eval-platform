# Datasets API Documentation (Frontend Integration Guide)

This document is written for AI coding agents working on the frontend to understand the strict schema requirements for the Datasets API.

## 1. Dataset Schema Definition

When creating or updating a Dataset, the backend requires a strict `schema` object. This schema defines the structure of the variables that will be used across all test cases inside the dataset.

**Important Changes:**
- The root level of the `schema` object must **strictly** contain only `"inputs"` and `"outputs"`.
- Any other root-level properties (e.g., `"metadata"`, `"config"`) sent by the frontend will be automatically pruned and ignored by the backend.

### Payload Example (Create/Update Dataset)
```json
{
  "name": "My Support Dataset",
  "schema": {
    "inputs": {
      "query": "string (Required: the main user input)",
      "image_id": "string (Optional: ID of an uploaded image)",
      "custom_user_trait": "string (Optional: any custom variable)"
    },
    "outputs": {
      "expected_output": "string (Optional: the ideal response)"
    }
  }
}
```

## 2. Test Case File Uploads (.json / .csv)

When the user uploads a `.json` or `.csv` file via the `/v1/datasets/upload` endpoint, the file contents must conform to the following rules. The legacy fields (`input_text`, `input_files`) have been **completely removed**.

### JSON Format Requirements
Test cases must be an array of objects. Each object must have an `"inputs"` dictionary and optionally an `"outputs"` dictionary.
- **CRITICAL:** The `"inputs"` dictionary **MUST** contain a `"query"` key. If it is missing, the backend will return a 400 Bad Request.
- Extra fields provided in the JSON are natively supported and will be appended as custom variables (accessible in the Metric Builder via the `testcase.` prefix).

**Valid JSON Example:**
```json
[
  {
    "inputs": {
      "query": "How do I reset my password?",
      "image_id": "f_12345abcd",
      "customer_tier": "enterprise"
    },
    "outputs": {
      "expected_output": "Go to settings > reset password."
    }
  }
]
```

### CSV Format Requirements
CSV files are parsed as flat dictionaries. 
- The backend will map the `"expected_output"` column to the `outputs` block. 
- All other columns will be mapped into the `inputs` block.
- **CRITICAL:** The CSV **MUST** contain a `"query"` column.

**Valid CSV Example:**
```csv
query,expected_output,customer_tier
"How do I reset my password?","Go to settings > reset password.","enterprise"
"Where is the billing page?","Click the billing tab.","free"
```

## 3. UI Implementation Tasks for the Frontend
1. **Dataset Creation Modal:** Ensure the UI for creating/updating a Dataset's schema builder explicitly generates an `inputs` and `outputs` block. It should force the `query` field to exist inside `inputs`.
2. **File Upload Validator:** (Optional but recommended) Add client-side pre-validation when uploading a JSON or CSV to warn the user if the required `"query"` field/column is missing before hitting the backend.
3. **Metric Builder Context:** When the frontend passes context to the Metric Builder, ensure it displays `testcase.inputs.query` and `testcase.outputs.expected_output` as standard variables, alongside any custom variables parsed from the dataset schema.
