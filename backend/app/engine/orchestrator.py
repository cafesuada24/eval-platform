import asyncio
import os
import re

import yaml
from app.engine.asserter import evaluate_threshold
from app.engine.executor import execute_ai_judge_async
from app.engine.resolver import (
    SYSTEM_EXTRACTOR_REGISTRY,
    format_prompt,
    resolve_bindings,
)
from app.models.config import MetricConfig, PipelineConfig, PipelineMetric
from app.models.report import MetricRunResult, PipelineResult
from app.models.telemetry import RuntimeState

# Resolve paths relative to backend directory
FIXTURES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'fixtures'),
)


def load_metric_config(metric_name: str) -> MetricConfig:
    """Search and load a MetricConfig by name from fixtures/metrics/."""
    metrics_dir = os.path.join(FIXTURES_DIR, 'metrics')

    # Try matching filename first
    for filename in [f'{metric_name}.yaml', f'{metric_name}.yml']:
        path = os.path.join(metrics_dir, filename)
        if os.path.exists(path):
            with open(path) as f:
                data = yaml.safe_load(f)
                if data and data.get('name') == metric_name:
                    return MetricConfig(**data)

    # Fallback: scan all yaml files for one with matching 'name' field
    if os.path.exists(metrics_dir):
        for entry in os.listdir(metrics_dir):
            if entry.endswith(('.yaml', '.yml')):
                path = os.path.join(metrics_dir, entry)
                with open(path) as f:
                    data = yaml.safe_load(f)
                    if data and data.get('name') == metric_name:
                        return MetricConfig(**data)

    raise FileNotFoundError(
        f"Metric configuration with name '{metric_name}' not found in fixtures/metrics/",
    )


def load_pipeline_config(pipeline_name: str) -> PipelineConfig:
    """Search and load a PipelineConfig by name from fixtures/pipelines/."""
    pipelines_dir = os.path.join(FIXTURES_DIR, 'pipelines')

    # Try matching filename first
    for filename in [f'{pipeline_name}.yaml', f'{pipeline_name}.yml']:
        path = os.path.join(pipelines_dir, filename)
        if os.path.exists(path):
            with open(path) as f:
                data = yaml.safe_load(f)
                if data and data.get('name') == pipeline_name:
                    return PipelineConfig(**data)

    # Fallback: scan all yaml files for one with matching 'name' field
    if os.path.exists(pipelines_dir):
        for entry in os.listdir(pipelines_dir):
            if entry.endswith(('.yaml', '.yml')):
                path = os.path.join(pipelines_dir, entry)
                with open(path) as f:
                    data = yaml.safe_load(f)
                    if data and data.get('name') == pipeline_name:
                        return PipelineConfig(**data)

    raise FileNotFoundError(
        f"Pipeline configuration with name '{pipeline_name}' not found in fixtures/pipelines/",
    )


def parse_formula(formula: str) -> tuple[str, str | None, float | None]:
    """
    Parses a simple operation expression like 'latency_ms / 1000' or 'latency_ms'.
    Returns (variable_name, operator, operand).
    """
    formula = formula.strip()
    # Pattern to match: <variable> <operator> <number>
    # Operators allowed: /, *, +, -
    pattern = r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*([/*+-])\s*([+-]?\d*(?:\.\d+)?)$"
    match = re.match(pattern, formula)
    if match:
        var_name = match.group(1)
        operator = match.group(2)
        try:
            operand = float(match.group(3))
            return var_name, operator, operand
        except ValueError:
            pass

    # If it is just a plain variable name
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", formula):
        return formula, None, None

    raise ValueError(
        f"Invalid formula expression: '{formula}'. Must be a variable name or a simple operation like 'variable / 1000'."
    )


async def _run_single_metric(
    state: RuntimeState,
    metric_item: PipelineMetric,
) -> MetricRunResult:
    """Fetch config, resolve variables, render prompt, execute async LLM or run primitive metric, assert status."""
    config = load_metric_config(metric_item.metric_name)

    if config.type == 'primitive':
        formula_str = config.formula
        if not formula_str:
            target = config.required_inputs[0] if config.required_inputs else None
            if not target:
                raise ValueError(
                    f"Primitive metric '{config.name}' must specify a formula or at least one required_input."
                )
            formula_str = target

        # Parse formula expression
        target, op, operand = parse_formula(formula_str)

        if target not in SYSTEM_EXTRACTOR_REGISTRY:
            raise ValueError(
                f"Extraction target '{target}' in primitive metric '{config.name}' is not supported by the system extractor registry."
            )

        extractor = SYSTEM_EXTRACTOR_REGISTRY[target]
        value = extractor(state)
        if value is None:
            raise ValueError(
                f"Required primitive metric target '{target}' could not be extracted from the runtime state."
            )

        try:
            score = float(value)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Extracted value for '{target}' is not numeric and cannot be scored for primitive metric: {value}"
            ) from e

        justification = f"Directly extracted '{target}' value: {score}."
        if op and operand is not None:
            if op == '*':
                score = score * operand
                justification = (
                    f"Extracted '{target}' ({value}) and multiplied by {operand}."
                )
            elif op == '/':
                if operand == 0:
                    raise ZeroDivisionError(
                        f"Math transformation division by zero in metric '{config.name}'."
                    )
                score = score / operand
                justification = (
                    f"Extracted '{target}' ({value}) and divided by {operand}."
                )
            elif op == '+':
                score = score + operand
                justification = f"Extracted '{target}' ({value}) and added {operand}."
            elif op == '-':
                score = score - operand
                justification = (
                    f"Extracted '{target}' ({value}) and subtracted {operand}."
                )

        assertion_status = evaluate_threshold(score, metric_item.threshold)
        return MetricRunResult(
            metric_name=metric_item.metric_name,
            score=score,
            justification=justification,
            assertion_status=assertion_status,
        )

    bindings = resolve_bindings(state, config.required_inputs)
    if not config.prompt_template:
        raise ValueError(
            f"AI-judge metric '{config.name}' must have a prompt_template."
        )
    prompt = format_prompt(config.prompt_template, bindings)
    judge_output = await execute_ai_judge_async(config, prompt)
    assertion_status = evaluate_threshold(judge_output.score, metric_item.threshold)

    return MetricRunResult(
        metric_name=metric_item.metric_name,
        score=judge_output.score,
        justification=judge_output.justification,
        assertion_status=assertion_status,
    )


async def execute_pipeline(
    state: RuntimeState,
    pipeline: PipelineConfig,
) -> PipelineResult:
    """Run all metrics in a pipeline concurrently and aggregate outcomes."""
    tasks = [_run_single_metric(state, metric_item) for metric_item in pipeline.metrics]
    results = await asyncio.gather(*tasks)

    # Determine overall status:
    # 1. fail if any metric fails
    # 2. warning if any metric warnings
    # 3. pass otherwise
    overall_status = 'pass'
    for r in results:
        if r.assertion_status == 'fail':
            overall_status = 'fail'
            break
    else:
        for r in results:
            if r.assertion_status == 'warning':
                overall_status = 'warning'
                break

    return PipelineResult(
        trace_id=state.trace_id,
        pipeline_name=pipeline.name,
        overall_status=overall_status,
        metric_results=list(results),
    )
