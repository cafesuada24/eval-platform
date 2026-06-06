import asyncio
from typing import Any

from app.core.eval_engine.extractors.runtime_state_extractor import (
    RuntimeStateExtractorService,
)
from app.core.eval_engine.models import (
    AssertionStatus,
    EvaluationContext,
    Metric,
    MetricRunResult,
    MetricThreshold,
)
from app.core.eval_engine.ports import AIJudgeService
from app.core.eval_engine.services.formula_evaluator import FormulaEvaluatorService
from jinja2 import Template


class MetricEvaluatorService:
    """Metric evaluation service."""

    def __init__(
        self,
        rs_extractor: RuntimeStateExtractorService,
        formula_evaluator: FormulaEvaluatorService,
        ai_judge_service: AIJudgeService,
    ) -> None:
        self.__formula_evaluator = formula_evaluator
        self.__rs_extractor = rs_extractor
        self.__ai_judge_service = ai_judge_service

    @staticmethod
    def __evaluate_threshold(
        score: float,
        threshold: MetricThreshold | None = None,
    ) -> AssertionStatus:
        """Evaluates a metric's score against optional semantic thresholds in order of severity.

        1. Critical failures (fail_over, fail_below)
        2. Warnings (warning_over, warning_below)
        Returns "pass" if no boundaries are breached.
        """
        if not threshold:
            return AssertionStatus.PASS

        # Evaluate rules in order of severity:
        # 1. Check fail thresholds first
        if threshold.fail_over is not None and score > threshold.fail_over:
            return AssertionStatus.FAIL
        if threshold.fail_below is not None and score < threshold.fail_below:
            return AssertionStatus.FAIL

        # 2. Check warning thresholds second
        if threshold.warning_over is not None and score > threshold.warning_over:
            return AssertionStatus.WARNING
        if threshold.warning_below is not None and score < threshold.warning_below:
            return AssertionStatus.WARNING

        return AssertionStatus.PASS

    @staticmethod
    def __format_prompt(
        template_str: str,
        bindings: dict[str, float | str | int],
    ) -> str:
        """Renders a Jinja2 template with resolved variable bindings."""
        template = Template(template_str)

        # Unflatten bindings so Jinja can resolve dot notation (e.g. testcase.inputs.text)
        unflattened_bindings: dict[str, Any] = {}
        for key, value in bindings.items():
            parts = key.split('.')
            current = unflattened_bindings
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value

        return template.render(**unflattened_bindings)

    def __resolve_bindings(
        self,
        variables: list[str],
        context: EvaluationContext,
        as_float: bool = False,
    ) -> dict[str, float | str | int]:
        resolved_bindings: dict[str, float | str | int] = {}
        for var in variables:
            resolved_var = self.__rs_extractor.extract_variable(
                variable=var,
                context=context,
            )
            if resolved_var is None:
                raise ValueError(
                    f"Required metric target '{var}' "
                    'could not be extracted from the runtime state.',
                )

            if as_float:
                try:
                    resolved_bindings[var] = float(resolved_var)
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Extracted value for '{var}' is not numeric and cannot be scored for primitive metric: {resolved_var}",
                    ) from e
            else:
                resolved_bindings[var] = resolved_var

        return resolved_bindings

    def __evaluate_primitive_metric(
        self,
        metric: Metric,
        context: EvaluationContext,
        threshold: MetricThreshold | None = None,
    ) -> MetricRunResult:
        assert metric.type == 'primitive'

        target = None
        formula_str = metric.formula
        if not formula_str:
            target = metric.required_inputs[0] if metric.required_inputs else None
            if not target:
                raise ValueError(
                    f"Primitive metric '{metric.name}' must specify a formula "
                    'or at least one required_input.',
                )
            formula_str = target

        required_vars = self.__formula_evaluator.get_required_variables(formula_str)
        resolved_vars = self.__resolve_bindings(required_vars, context, as_float=True)
        score = self.__formula_evaluator.evaluate_formula(
            formula=formula_str,
            var_bind=resolved_vars,
        )

        if target:
            justification = f"Directly extracted '{target}' value: {score}."
        else:
            justification = f"Evaluated formula '{formula_str}' to: {score}."

        assertion_status = self.__class__.__evaluate_threshold(score, threshold)
        return MetricRunResult(
            metric_id=metric.id,
            metric_name=metric.name,
            score=score,
            justification=justification,
            evidence=None,
            assertion_status=assertion_status,
        )

    async def __evaluate_ai_judge_metric(
        self,
        metric: Metric,
        context: EvaluationContext,
        building_mode: bool,
        threshold: MetricThreshold | None = None,
    ) -> MetricRunResult:
        if not metric.prompt_template:
            raise ValueError(
                f"AI-judge metric '{metric.name}' must have a prompt_template.",
            )
        bindings = self.__resolve_bindings(
            metric.required_inputs,
            context,
            as_float=False,
        )
        prompt = self.__format_prompt(metric.prompt_template, bindings)
        judge_output = await self.__ai_judge_service.evaluate(
            metric, prompt, building_mode=building_mode
        )
        assertion_status = self.__evaluate_threshold(
            judge_output.score,
            threshold,
        )

        return MetricRunResult(
            metric_id=metric.id,
            metric_name=metric.name,
            score=judge_output.score,
            justification='\n'.join(judge_output.justification),
            evidence='\n'.join(judge_output.evidence),
            improvements='\n'.join(judge_output.improvements)
            if judge_output.improvements
            else None,
            assertion_status=assertion_status,
        )

    async def evaluate(
        self,
        metric: Metric,
        context: EvaluationContext,
        threshold: MetricThreshold | None = None,
        building_mode: bool = False,
    ) -> MetricRunResult:
        """Evaluate a metric against a runtime state."""
        attempts = 3
        last_error = None
        is_value_error = False

        for attempt in range(attempts):
            try:
                if metric.type == 'primitive':
                    return self.__evaluate_primitive_metric(
                        metric=metric,
                        context=context,
                        threshold=threshold,
                    )

                return await self.__evaluate_ai_judge_metric(
                    metric=metric,
                    context=context,
                    threshold=threshold,
                    building_mode=building_mode,
                )
            except ValueError as e:
                last_error = e
                is_value_error = True
                if attempt < attempts - 1:
                    await asyncio.sleep(0.5)
            except Exception as e:
                last_error = e
                is_value_error = False
                if attempt < attempts - 1:
                    await asyncio.sleep(0.5)

        if is_value_error:
            return MetricRunResult(
                metric_id=metric.id,
                metric_name=metric.name,
                score=0.0,
                justification=f'Execution failed due to missing required variables or format error after {attempts} attempts: {str(last_error)}',
                evidence=None,
                assertion_status=AssertionStatus.WARNING,
            )
        return MetricRunResult(
            metric_id=metric.id,
            metric_name=metric.name,
            score=0.0,
            justification=f'Execution failed due to an unexpected error (e.g., LLM API failure) after {attempts} attempts: {str(last_error)}',
            evidence=None,
            assertion_status=AssertionStatus.WARNING,
        )
