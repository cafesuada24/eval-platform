"""Multi-step evaluators for rigorous evaluation of RAG metrics."""

from typing import Any, Literal
import litellm
from pydantic import BaseModel, TypeAdapter
from app.core.eval_engine.models import JudgeResult, Metric
from app.infra.services.ai_judge_service import _get_litellm_model_name


# --- Pydantic Schema Models for Structured Output Validation ---

class ClaimsList(BaseModel):
    """Pydantic schema representing a list of claims/facts extracted from text."""
    claims: list[str]


class ClaimVerdict(BaseModel):
    """Factual verification result for a single claim against the context."""
    claim: str
    verdict: Literal["supported", "refuted", "neutral"]
    reason: str


class ClaimVerificationResponse(BaseModel):
    """Wrapper response schema for claims verification."""
    verifications: list[ClaimVerdict]


class StatementsList(BaseModel):
    """Pydantic schema representing a list of statements extracted from text."""
    statements: list[str]


class StatementVerdict(BaseModel):
    """Relevancy verification result for a single statement against the query."""
    statement: str
    relevant: bool
    reason: str


class StatementRelevancyResponse(BaseModel):
    """Wrapper response schema for statement relevancy."""
    verdicts: list[StatementVerdict]


class RecallVerdict(BaseModel):
    """Recall verification result for a ground-truth claim in the retrieved context."""
    claim: str
    recalled: bool
    reason: str


class RecallVerificationResponse(BaseModel):
    """Wrapper response schema for context recall."""
    verdicts: list[RecallVerdict]


# --- Helper Methods ---

async def _call_llm_structured(
    metric: Metric,
    system_prompt: str,
    user_prompt: str,
    response_schema: type[BaseModel],
) -> Any:
    """Calls LiteLLM's structured generation with a strict Pydantic JSON schema."""
    import json
    model_name = _get_litellm_model_name(metric)
    temperature = (
        metric.model_configuration.temperature
        if metric.model_configuration
        else 0.0
    )

    ta = TypeAdapter(response_schema)
    schema_str = json.dumps(ta.json_schema())
    
    # Inject JSON schema instructions into system prompt
    enhanced_system_prompt = (
        f"{system_prompt}\n\n"
        "You MUST return your output ONLY as a JSON object matching this JSON schema:\n"
        f"{schema_str}\n\n"
        "Do not include any markdown styling, code block wrappers (such as ```json), conversational filler, or extra text. Output ONLY raw, valid JSON."
    )

    messages = [
        {"role": "system", "content": enhanced_system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = await litellm.acompletion(
        model=model_name,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": ta.json_schema(),
            "strict": True,
        },
        temperature=temperature,
    )

    if not response.choices or response.choices[0].message.content is None:
        raise ValueError("LLM returned an empty or invalid response")

    content = response.choices[0].message.content.strip()
    
    # Strip markdown wrappers if present
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return ta.validate_json(content)


def _get_binding_value(
    bindings: dict[str, Any],
    key: str,
    fallback_substrings: list[str] | None = None,
) -> str:
    """Safely extracts a string value from bindings using direct match, dotted end, or substrings."""
    if key in bindings:
        return str(bindings[key])

    # Check dotted notation ending in the key (e.g. testcase.expected_outputs.expected_output matches expected_output)
    for k, v in bindings.items():
        if k.endswith(f".{key}"):
            return str(v)

    if fallback_substrings:
        for f_sub in fallback_substrings:
            for k, v in bindings.items():
                if f_sub in k:
                    return str(v)

    raise KeyError(f"Required key '{key}' not found in bindings: {list(bindings.keys())}")


# --- Workflow Implementations ---

async def evaluate_faithfulness_rigorous(
    metric: Metric,
    bindings: dict[str, Any],
) -> JudgeResult:
    """Rigorous Faithfulness Metric: Checks that output claims are supported by context."""
    retrieved_context = _get_binding_value(bindings, "retrieved_context", ["context"])
    output_text = _get_binding_value(bindings, "output_text", ["output", "response"])

    # Step 1: Claim Extraction
    system_prompt_extract = (
        "You are a helpful assistant. Your task is to extract all atomic factual claims from the given text. "
        "Each claim should be a single, simple, standalone fact."
    )
    user_prompt_extract = f"Text:\n{output_text}"

    claims_response = await _call_llm_structured(
        metric=metric,
        system_prompt=system_prompt_extract,
        user_prompt=user_prompt_extract,
        response_schema=ClaimsList,
    )

    claims = claims_response.claims
    if not claims:
        return JudgeResult(
            score=1.0,
            justification=["No claims extracted from output_text."],
            evidence=["No claims extracted."],
            improvements=None,
        )

    # Step 2: Claim Verification
    system_prompt_verify = (
        "You are an objective AI evaluation judge. Your task is to verify each claim against the retrieved context. "
        "For each claim, decide if it is 'supported', 'refuted', or 'neutral' based strictly on the context. "
        "Provide a clear reasoning for each verdict."
    )
    user_prompt_verify = (
        f"Context:\n{retrieved_context}\n\n"
        f"Claims:\n" + "\n".join(f"- {c}" for c in claims)
    )

    verification_response = await _call_llm_structured(
        metric=metric,
        system_prompt=system_prompt_verify,
        user_prompt=user_prompt_verify,
        response_schema=ClaimVerificationResponse,
    )

    verifications = verification_response.verifications

    # Calculate ratio score
    supported_count = sum(
        1 for v in verifications if v.verdict.lower() == "supported"
    )
    total_claims = len(verifications)
    score = supported_count / total_claims if total_claims > 0 else 1.0

    # Compile justification & evidence
    justification: list[str] = []
    evidence: list[str] = []

    for v in verifications:
        detail = f"Claim: '{v.claim}' | Verdict: {v.verdict} | Reason: {v.reason}"
        justification.append(detail)
        evidence.append(detail)

    return JudgeResult(
        score=score,
        justification=justification,
        evidence=evidence,
        improvements=None,
    )


async def evaluate_answer_relevancy_rigorous(
    metric: Metric,
    bindings: dict[str, Any],
) -> JudgeResult:
    """Rigorous Answer Relevancy Metric: Evaluates if generated statements address the query."""
    input_text = _get_binding_value(bindings, "input_text", ["input", "query"])
    output_text = _get_binding_value(bindings, "output_text", ["output", "response"])

    # Step 1: Statement Extraction
    system_prompt_extract = (
        "You are a helpful assistant. Your task is to extract all standalone sentences/statements from the output text. "
        "Each statement should represent a single point made."
    )
    user_prompt_extract = f"Output text:\n{output_text}"

    statements_response = await _call_llm_structured(
        metric=metric,
        system_prompt=system_prompt_extract,
        user_prompt=user_prompt_extract,
        response_schema=StatementsList,
    )

    statements = statements_response.statements
    if not statements:
        return JudgeResult(
            score=1.0,
            justification=["No statements extracted from output_text."],
            evidence=["No statements extracted."],
            improvements=None,
        )

    # Step 2: Relevancy Assessment
    system_prompt_verify = (
        "You are an objective AI evaluation judge. Your task is to assess whether each statement from the response "
        "is relevant to answering the user query. Classify each statement as relevant (true) or irrelevant (false) "
        "along with the reasoning."
    )
    user_prompt_verify = (
        f"Query:\n{input_text}\n\n"
        f"Statements:\n" + "\n".join(f"- {s}" for s in statements)
    )

    relevancy_response = await _call_llm_structured(
        metric=metric,
        system_prompt=system_prompt_verify,
        user_prompt=user_prompt_verify,
        response_schema=StatementRelevancyResponse,
    )

    verdicts = relevancy_response.verdicts

    # Calculate ratio score
    relevant_count = sum(1 for v in verdicts if v.relevant)
    total_statements = len(verdicts)
    score = relevant_count / total_statements if total_statements > 0 else 1.0

    # Compile justification & evidence
    justification: list[str] = []
    evidence: list[str] = []

    for v in verdicts:
        status = "relevant" if v.relevant else "irrelevant"
        detail = (
            f"Statement: '{v.statement}' | Relevancy: {status} | Reason: {v.reason}"
        )
        justification.append(detail)
        evidence.append(detail)

    return JudgeResult(
        score=score,
        justification=justification,
        evidence=evidence,
        improvements=None,
    )


async def evaluate_context_recall_rigorous(
    metric: Metric,
    bindings: dict[str, Any],
) -> JudgeResult:
    """Rigorous Context Recall Metric: Assesses if ground-truth facts are recalled in context."""
    retrieved_context = _get_binding_value(bindings, "retrieved_context", ["context"])
    expected_output = _get_binding_value(
        bindings,
        "testcase.expected_outputs.expected_output",
        ["expected_output", "ground_truth"],
    )

    # Step 1: Claim Extraction from Ground Truth
    system_prompt_extract = (
        "You are a helpful assistant. Your task is to extract all atomic factual claims from the expected output. "
        "Each claim should represent a single fact/statement of truth."
    )
    user_prompt_extract = f"Expected output:\n{expected_output}"

    claims_response = await _call_llm_structured(
        metric=metric,
        system_prompt=system_prompt_extract,
        user_prompt=user_prompt_extract,
        response_schema=ClaimsList,
    )

    claims = claims_response.claims
    if not claims:
        return JudgeResult(
            score=1.0,
            justification=["No claims extracted from expected output."],
            evidence=["No claims extracted."],
            improvements=None,
        )

    # Step 2: Recall Verification
    system_prompt_verify = (
        "You are an objective AI evaluation judge. Your task is to verify whether each claim extracted from the expected output "
        "can be recalled/found in the retrieved context. For each claim, decide if it is recalled (true) or not recalled (false) "
        "based strictly on the context, providing a clear reason."
    )
    user_prompt_verify = (
        f"Retrieved context:\n{retrieved_context}\n\n"
        f"Claims to verify:\n" + "\n".join(f"- {c}" for c in claims)
    )

    recall_response = await _call_llm_structured(
        metric=metric,
        system_prompt=system_prompt_verify,
        user_prompt=user_prompt_verify,
        response_schema=RecallVerificationResponse,
    )

    verdicts = recall_response.verdicts

    # Calculate ratio score
    recalled_count = sum(1 for v in verdicts if v.recalled)
    total_claims = len(verdicts)
    score = recalled_count / total_claims if total_claims > 0 else 1.0

    # Compile justification & evidence
    justification: list[str] = []
    evidence: list[str] = []

    for v in verdicts:
        status = "recalled" if v.recalled else "not recalled"
        detail = (
            f"Claim: '{v.claim}' | Recall status: {status} | Reason: {v.reason}"
        )
        justification.append(detail)
        evidence.append(detail)

    return JudgeResult(
        score=score,
        justification=justification,
        evidence=evidence,
        improvements=None,
    )
