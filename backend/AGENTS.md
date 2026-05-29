# EvalPlatform: Backend Core
> The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.

## 1. Backend Principles

| Principle | Technical Implication |
| :--- | :--- |
| **Canonical Runtime State** | All ingested telemetry is flattened into a strict, validated `RuntimeState` Pydantic model. |
| **Absolute Zero-Config Pipelines** | Users NEVER map variables. The Agent selects known variables, and the backend extracts them natively via an Extractor Registry. |
| **Semantic Assertions** | Pipelines use simple, readable boundaries (e.g., `fail_below`, `warning_over`) to assert pipeline health without complex math operators. |
| **Provider-Agnostic Execution** | User-defined metrics are executed through `litellm`. |
| **YAML as Source of Truth** | Metrics store their own context and descriptions. The Agent reads this YAML dynamically to understand the metric it is building or editing. |
| **Event-Driven** | Runtime events are the absolute source of truth |
| **Framework-Agnostic** | No framework-specific internal contracts |
| **Metric Composability** | Primitive metrics compose into logical evaluation pipelines |
| **Multimodal-First** | Artifacts (images, PDFs, text) are first-class citizens |

---

## 2. Domain Lexicon

### Core Telemetry Models
* **`RuntimeEvent`**: A discrete occurrence pushed by the SDK (e.g., `generation.start`).
* **`RuntiPipeline Orchestrator: The async execution engine that takes a single RuntimeState and a PipelineConfig, fanning out concurrent requests to the execute_ai_judge and compiling the final report.meState`**: The aggregated, normalized payload of a single chat turn.


### Evaluation Entities
* **`MetricConfig`**: A YAML configuration defining a metric's `description` (agent's context), scoring scale, required system variables, and a Jinja2 template.
* **`PipelineConfig`**: A YAML configuration grouping metrics. It contains only the metric names and their optional semantic assertion thresholds. (No variable bindings).
* **`Threshold`**: Semantic boundaries applied to a metric's final score: `fail_over`, `fail_below`, `warning_over`, or `warning_below`.
* **`Extractor Registry`**: A strict Python dictionary mapping known variable names (e.g., `retrieved_context`) to specific extraction functions.
* **`Metric Agent`**: An internal service powered by `google-genai` using tool-calling to build Metric configs autonomously based on the current YAML state and the Extractor Registry.
* **`Pipeline Orchestrator`**: The async execution engine that takes a single RuntimeState and a PipelineConfig, fanning out concurrent requests to the execute_ai_judge and compiling the final report.
* **`Pipeline Result`**: The aggregated output of an orchestrated run. It contains the individual scores for each metric, plus an overall_status (Pass/Fail/Warning). A pipeline fails if any single metric breaches a fail threshold.
---

## 3. System Architecture & Tech Stack

* **API Framework:** `fastapi` & `uvicorn` (Asynchronous event ingestion).
* **Validation & Serialization:** `pydantic` (Strict type checking).
* **Template & Parsing:** `pyyaml`, `jinja2` (Config parsing and prompt rendering).
* **Execution Engine:** `litellm` (Provider-agnostic metric execution).
* **Agent Engine:** `google-genai` (Internal metric builder service).

> **Development Instruction:** Always use `context7` to pull the latest documentation and reference implementations for the packages listed above during active development.

---

## 4. Backend Directory Structure

```text
backend
├── AGENTS.md
├── API.md
├── app
│   ├── api
│   │   └── v1
│   ├── core
│   │   ├── agents        # Agent features
│   │   ├── config.py
│   │   ├── eval_engine   # Evaluation engine feature
│   │   ├── exceptions.py
│   │   ├── shared        # Shared stuff
│   ├── infra
│   │   ├── agents
│   │   ├── dtos
│   │   ├── __init__.py
│   │   └── services
│   └── main.py
├── fixtures
│   ├── chromadb
│   ├── metrics                 
│   ├── pipelines
│   ├── sessions
│   └── uploads
├── pyproject.toml
├── README.md
└── tests
```

## 5. Code format
* Always adhere to Python 3.12 best practices
* Always include type hint
* Use context7-mcp if you need library reference
