import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.engine.resolver import SYSTEM_EXTRACTOR_REGISTRY

class ModelConfigToolInput(BaseModel):
    provider: str = Field(description="The model provider, e.g., 'anthropic' or 'google'")
    model: str = Field(description="The model name, e.g., 'claude-3-5-sonnet' or 'gemini-2.5-flash'")

class ScoringScaleToolInput(BaseModel):
    min: float = Field(description="The minimum possible score value")
    max: float = Field(description="The maximum possible score value")
    data_type: str = Field(description="The data type of the score, e.g., 'integer' or 'float'")

class UpdateMetricConfigTool(BaseModel):
    """
    Form parameters to update or create a MetricConfig.
    """
    name: str = Field(description="The unique name of the metric (e.g., hallucination_ai_judge)")
    type: str = Field(description="The type of the metric (e.g., 'ai-judge')")
    description: str = Field(description="A clear description of the metric, explaining what it evaluates")
    model_configuration: ModelConfigToolInput = Field(description="Configuration of the model used for evaluation")
    required_inputs: List[str] = Field(description="Variables required by the metric template, selected ONLY from SYSTEM_EXTRACTOR_REGISTRY.")
    prompt_template: str = Field(description="The Jinja2 prompt template using selected variables")
    scoring_scale: ScoringScaleToolInput = Field(description="The minimum/maximum values and type of the metric score")

class MetricAgentService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the google-genai client.
        If api_key is omitted, client reads from GEMINI_API_KEY env variable.
        """
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def chat_with_agent(
        self,
        messages: List[Dict[str, str]],
        current_yaml_config: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interact with the AI Metric Builder agent.
        Injects the Extractor Registry and the current YAML state into the system instruction,
        and registers the UpdateMetricConfigTool.
        """
        allowed_vars = list(SYSTEM_EXTRACTOR_REGISTRY.keys())

        system_instruction = (
            "You are an expert AI Metric Builder.\n\n"
            "CRITICAL RULES:\n"
            "1. You must autonomously decide which system variables are required.\n"
            f"2. You MUST select variables ONLY from this exact list: {allowed_vars}. Do not invent variables.\n"
            "3. Write the Jinja2 template using your selected variables, write a clear metric `description` explaining the metric, "
            "and invoke UpdateMetricConfigTool to save or update the configuration.\n"
        )

        if current_yaml_config:
            system_instruction += f"\nCURRENT METRIC STATE:\n```yaml\n{current_yaml_config}\n```\n"

        # Format messages into google-genai SDK Content structures
        formatted_contents = []
        for msg in messages:
            formatted_contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        called_tool_args = []

        # Real function tool that Gemini invokes. Docstrings and signatures are automatically
        # converted into tool FunctionDeclarations by the SDK.
        def update_metric_config(
            name: str,
            type: str,
            description: str,
            model_configuration: dict,
            required_inputs: List[str],
            prompt_template: str,
            scoring_scale: dict
        ) -> str:
            """
            Updates or creates the metric configuration with the specified parameters.

            Args:
                name: The unique name of the metric (e.g., hallucination_ai_judge)
                type: The type of metric, typically 'ai-judge'
                description: Clear explanation of what the metric evaluates and when to use it
                model_configuration: Dict containing 'provider' and 'model'
                required_inputs: List of variables from SYSTEM_EXTRACTOR_REGISTRY
                prompt_template: The Jinja2 prompt template for the metric
                scoring_scale: Dict containing 'min', 'max', 'data_type'
            """
            # Validate required_inputs against registry
            for var in required_inputs:
                if var not in allowed_vars:
                    return f"Error: Variable '{var}' is not supported. Allowed: {allowed_vars}"

            tool_input = {
                "name": name,
                "type": type,
                "description": description,
                "model_configuration": model_configuration,
                "required_inputs": required_inputs,
                "prompt_template": prompt_template,
                "scoring_scale": scoring_scale
            }
            called_tool_args.append(tool_input)
            return "Success: Metric configuration successfully updated."

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[update_metric_config],
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=formatted_contents,
            config=config
        )

        return {
            "response_text": response.text,
            "called_tool_args": called_tool_args
        }
