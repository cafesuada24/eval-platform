# Frontend Implementation Plan

**Objective:** Build a responsive, highly interactive Next.js dashboard emphasizing seamless state synchronization between an AI Agent and visual form components.

## Phase 1: App Shell & Global UX
**Goal:** Establish a premium, dark-mode ready developer environment.

1.  **Initialize & Theme (`src/app/layout.tsx`)**:
    * Install Tailwind, `shadcn/ui` (Button, Input, Table, Card, Badge, Dropdown, Tabs, Slider, SplitPane).
    * Configure a professional dark/light theme (slate or zinc color palette).
2.  **Sidebar Navigation**:
    * Build a persistent sidebar containing links to "Pipelines", "Metrics", and "Playground".
    * Ensure active states highlight cleanly.

---

## Phase 2: Metrics & Pipeline Management (The CRUD Views)
**Goal:** Build clean, intuitive tables and forms for managing observability rules.

1.  **Metrics List (`src/app/metrics/page.tsx`)**:
    * Render a `DataTable`. Columns: Name, Type (`Badge`), Model, and Actions.
    * **UX Rule:** If `type === 'primitive'`, gray out the Edit button and wrap it in a `Tooltip` ("System metrics cannot be edited"). 
2.  **Pipeline Detail View (`src/app/pipelines/[id]/page.tsx`)**:
    * Render the Pipeline Name and Description.
    * Render a list of `PipelineMetricCard` components.
    * **The Semantic Threshold Builder:** For each metric in the pipeline, render a clean form to add rules.
      * *Dropdown:* "Fail Over", "Fail Below", "Warning Over", "Warning Below".
      * *Input:* Numeric value.
      * *Visuals:* Use a red text/border for 'Fail' rules, and amber for 'Warning' rules to instantly communicate severity.

---

## Phase 3: The Metric Playground (Split-Pane Layout)
**Goal:** Build the container for the Agent/Configurator workflow.

1.  **Layout Construction (`src/components/playground/`)**:
    * Use a resizable split-pane component.
    * **Left Pane (`AgentChat.tsx`)**: Render a chat interface with an input box fixed to the bottom. Render user/assistant message bubbles.
    * **Right Pane (`MetricConfigurator.tsx`)**: Render a `Tabs` component (`value="prompt"` and `value="model"`).

2.  **Configurator Forms**:
    * **Tab 1 (Prompt):** Name Input, Prompt Textarea, Min/Max Score inputs, Data Type dropdown (`Integer`/`Float`).
      * Render a `Badge` list for `required_inputs`. If the variable matches a known system extractor (e.g., `output_text`), append a green "✅ Auto-bound" tag.
      * Render the muted info banner explaining the hidden JSON system instruction.
    * **Tab 2 (Model):** Provider dropdown, Model Name input, Temperature Slider (0.0 - 1.0).

---

## Phase 4: Agentic State Sync (The "Magic" UX)
**Goal:** Connect the backend Gemini agent to the React UI state seamlessly.

1.  **Vercel AI SDK Integration (`src/components/playground/AgentChat.tsx`)**:
    * Implement `useChat({ api: '/api/agent' })`.
    * Ensure the chat payload includes the `current_yaml_config` (stringified current state of the right pane) so the backend agent has context.
2.  **Tool Interception & Form Patching**:
    * Monitor the `toolInvocations` array from the `useChat` hook.
    * When the agent calls `UpdateMetricConfigTool`, intercept the payload (`prompt_template`, `min_score`, `required_inputs`, etc.).
    * Automatically patch the React state (or `react-hook-form` values) for the `MetricConfigurator` pane.
    * **Feedback Loop:** Render a custom chat bubble in the Left Pane stating: *"✨ Agent updated the configuration panel"* instead of rendering raw JSON to the user.

---

## Phase 5: Polish & Edge Cases
**Goal:** Ensure the app feels bulletproof.

1.  **Empty States & Skeletons**:
    * Design beautiful empty states for the Pipelines page (e.g., "No pipelines found. Create your first observability pipeline to start evaluating traces.").
    * Use `shadcn/ui` Skeleton components during data fetching.
2.  **Toast Notifications**:
    * Implement success/error toasts when saving a Pipeline or Metric.
3.  **Client-Side Validation (`zod`)**:
    * Ensure the frontend strictly validates that `min_score` is less than `max_score` before allowing a user to save the metric config.
---
