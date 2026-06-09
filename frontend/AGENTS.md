# EvalPlatform: Frontend Dashboard
> The premium Next.js developer interface for managing pipelines, defining semantic thresholds, and interacting with the Agentic Metric Builder.

## 1. UX/UI Principles

| Principle | Technical Implication |
| :--- | :--- |
| **Agent-Driven UI (State Sync)** | Users shouldn't copy-paste from the chat. When the Gemini Agent calls the `UpdateMetricConfigTool`, the Vercel AI SDK must intercept it and instantly animate/update the React state on the configuration panel. |
| **Hide the YAML** | While the backend treats YAML as the source of truth, the UI abstracts it into clean forms, tabs, and sliders. YAML is only exposed if the user explicitly requests a "Code View." |
| **Visual Observability** | Semantic thresholds dictate visual hierarchy. Use strict color coding (Destructive/Red for `fail_over`/`fail_below`, Warning/Amber for `warning_over`/`warning_below`, Success/Green for `pass`). |
| **Zero-Config Validation** | When viewing metric variables, visually reward the user with a green "✅ Auto-bound to System State" badge if the variable exists in the backend's Extractor Registry, reducing cognitive load. |
| **Frictionless Navigation** | Utilize Next.js App Router for instant page transitions. Use slide-out sheets and modal dialogs for quick edits rather than heavy page unloads. |

---

## 2. Domain Lexicon (UI Context)

### Core Components
* **`Metric Builder`**: The flagship UI view. A resizable split-pane layout with the Agent Chat on the left and the Tabbed Configurator on the right.
* **`Tool Interceptor`**: The frontend logic (via Vercel AI SDK's `toolInvocations`) that listens for backend tool calls and patches the `react-hook-form` state.
* **`Semantic Threshold Builder`**: A custom form component allowing users to add assertion rules (e.g., "Fail if > 4.0") to metrics within a pipeline.

### UX Patterns
* **`Primitive vs. Custom`**: Primitive metrics (like Exact Match) have a disabled "Edit" button with a `Tooltip` explaining they are system-locked. Custom AI-Judges route to the Playground.
* **`Muted Info Banners`**: Subtle UI alerts placed below prompts explaining backend behaviors (e.g., "System automatically appends JSON formatting instructions at runtime").

---

## 3. System Architecture & Tech Stack

* **Core Framework:** `next` (App Router, React Server Components).
* **Styling & Components:** `tailwindcss`, `shadcn/ui`, `lucide-react`, `framer-motion` (for subtle layout animations).
* **Forms & Validation:** `react-hook-form` and `zod` (Strict client-side validation mirroring the backend Pydantic schemas).
* **AI Integration:** `ai` (Vercel AI SDK for streaming the Gemini agent chat and handling tool calls).
* **Data Fetching:** `swr` or `@tanstack/react-query` (For snappy, cached reads of metrics and pipelines).

> **Development Instruction:** Prioritize accessibility and dark-mode compatibility. All `shadcn/ui` components must be fully keyboard navigable. 

---

## 4. Dashboard Directory Structure

```text
frontend/
├── package.json
├── tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── metrics/                # Metrics Table View
│   │   ├── pipelines/              # Pipeline List & Detail View
│   │   ├── metric-builder/         # The Split-Pane Metric Editor
│   │   └── layout.tsx              # Sidebar Navigation Shell
│   ├── components/
│   │   ├── ui/                     # shadcn/ui primitives (Button, Input, Slider)
│   │   ├── metric-builder/         # AgentChat, MetricConfigurator, ToolInterceptor
│   │   └── pipelines/              # ThresholdBuilder, PipelineMetricCard
│   └── lib/
│       └── utils.ts                # Tailwind merge utils (cn)
```
