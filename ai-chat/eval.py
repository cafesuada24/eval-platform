"""Evaluation module for local pipeline evaluation."""

import os

from dotenv import load_dotenv
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.helpers import trace
from evalplatform_sdk.management import DatasetClient
from rag_engine import generate_answer, retrieve_context


def main() -> None:
    """Runs the main evaluation pipeline with the test cases dataset."""
    load_dotenv()

    # 1. Initialize the client
    client = EvalClient(
        api_key=os.environ.get('EVAL_API_KEY', 'dummy_key'),
        base_url=os.environ.get('EVAL_BASE_URL', 'http://localhost:8000'),
    )

    dataset = DatasetClient(
        client=client._management_client,
        base_url='http://localhost:8000',
    )
    # Mock dataset for evaluation
    cases = dataset.get_cases('a8ee38dc-8052-4ce4-b86b-fb69abefc781')
    print(f'Starting evaluation with {len(cases)} test cases...')

    # 2. Start an evaluation job
    evaluation = client.pipelines.start_evaluation(
        pipeline_id='7438d2d0-c075-4b0e-b923-ca78b4bcb19a',
        dataset_id='a8ee38dc-8052-4ce4-b86b-fb69abefc781',
    )

    for case in cases:
        # 3. Start tracking for this specific dataset row
        with (
            evaluation.track_case(case['id']) as case_tracker,
            trace(eval_tracker=case_tracker) as state,
        ):
            print(case)
            query = case['inputs']['query']

            # Retrieve context (automatically tracks retrieval via state)
            context, image_paths = retrieve_context(state, query)

            # Generate answer (automatically tracks generation via state)
            answer = generate_answer(state, query, context, image_paths)

            print(f'  Q: {query}')
            print(f'  A: {answer.strip()}')

    # 5. Non-blocking evaluation completion
    res = evaluation.complete(block=False)
    print(f'\nEvaluation job dispatched and completed locally. {res}')


if __name__ == '__main__':
    main()
