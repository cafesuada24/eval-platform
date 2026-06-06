# Context
You are a frontend specialist agent. Your goal is to implement the "Dataset Builder" interface for the EvalPlatform. The platform evaluates LLM applications, and this feature allows users to construct evaluation datasets dynamically.

Our backend has recently transitioned to a highly flexible, multimodal schema for Test Cases. Instead of rigid `input_text` strings, Test Cases now use dynamic `inputs` and `expected_outputs` dictionaries. Users can also upload binary files (e.g., images) directly to the dataset.

# API Contracts

You will interact with the following REST endpoints on the backend (`baseURL: /api/v1/datasets`):

### 1. Dataset Management
- **Create Dataset:** `POST /`
  - Body: `{ "name": "My New Dataset" }`
  - Returns: `Dataset` object.
- **Update Dataset:** `PATCH /{dataset_id}`
  - Body: `{ "name": "Updated Name" }`

### 2. File Uploads (Multimodal Assets)
- **Upload File:** `POST /{dataset_id}/files`
  - Body: `multipart/form-data` with a `file` field.
  - Returns: `{ "file_id": "f_123.png", "filename": "image.png", "url": "/api/v1/datasets/{id}/files/f_123.png" }`
  - *Note: Once uploaded, the user should copy/inject the `file_id` into their Test Case `inputs` dict.*

### 3. Test Cases
- **List Cases:** `GET /{dataset_id}/cases?page=1&limit=50`
  - Returns: Paginated array of `TestCase` objects.
- **Create Case:** `POST /{dataset_id}/cases`
  - Body: 
    ```json
    {
      "inputs": { "text": "...", "image_file_id": "f_123.png" },
      "expected_outputs": { "response": "..." },
      "metadata": { "difficulty": "hard" }
    }
    ```
- **Update Case:** `PUT /{dataset_id}/cases/{case_id}`
  - Body: Same as Create.
- **Delete Case:** `DELETE /{dataset_id}/cases/{case_id}`

# UI/UX Requirements

Please implement the page following these design requirements:

1. **Layout Structure:**
   - **Header:** Shows the Dataset Name (editable inline, triggers the `PATCH` endpoint) and global actions.
   - **Main Content:** A data grid or stack of cards representing the Test Cases.
   - **Sidebar / File Manager:** A drag-and-drop zone to upload files via the `POST /files` endpoint. It should list successfully uploaded files and provide a "Copy ID" button so users can easily paste the `file_id` into their testcases.

2. **Dynamic Key-Value Editor:**
   - Because `inputs`, `expected_outputs`, and `metadata` are dynamic dictionaries, standard text inputs won't work.
   - For each Test Case row, provide a dynamic Key-Value pair builder (e.g., Key: `image_file_id`, Value: `f_123.png`), or integrate a lightweight JSON editor component.
   - Users must be able to add, edit, and remove keys freely.

3. **Pagination & Performance:**
   - Datasets can contain thousands of rows. 
   - You MUST implement pagination utilizing the `page` and `limit` query parameters on the `GET /cases` endpoint. Implement standard Next/Previous buttons or infinite scrolling.

4. **Optimistic UI:**
   - When a user deletes a testcase, remove it from the UI immediately while the `DELETE` request processes in the background.

# Tech Stack & Implementation Rules
- **Components:** Create modular, reusable components (e.g., `TestCaseRow.tsx`, `DatasetFileManager.tsx`, `DynamicDictEditor.tsx`).
- **Styling:** Use TailwindCSS (or the project's established styling system).
- **Error Handling:** Gracefully display toast notifications if file uploads or row updates fail.
- **Types:** Strictly type the API responses based on the contracts provided above.
