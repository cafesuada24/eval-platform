"""Dataset parser service."""

import csv
import io
import json
from typing import Any
from uuid import uuid4

from app.core.eval_engine.models import Dataset, TestCase
from app.core.exceptions import DomainError


class InvalidDatasetError(DomainError):
    """Raised when a dataset file is invalid."""


class DatasetParserService:
    """Service to parse dataset files into Dataset entities."""

    def parse(self, filename: str, contents: bytes) -> Dataset:
        """Parse a dataset from bytes.

        Args:
            filename: Name of the uploaded file.
            contents: Raw bytes of the file.

        Returns:
            Parsed Dataset entity.

        Raises:
            InvalidDatasetError: If file format is unsupported or invalid.
        """
        if filename.endswith('.json'):
            test_cases = self._parse_json(contents)
        elif filename.endswith('.csv'):
            test_cases = self._parse_csv(contents)
        else:
            raise InvalidDatasetError('Only .json and .csv files are supported')

        return Dataset(
            id=uuid4(),
            name=filename,
            cases=test_cases,
        )

    def _parse_json(self, contents: bytes) -> list[TestCase]:
        """Parse a JSON file into test cases."""
        test_cases: list[TestCase] = []
        try:
            data = json.loads(contents.decode('utf-8'))
            if not isinstance(data, list):
                raise InvalidDatasetError('JSON must be a list of test cases')

            for item in data:
                if not isinstance(item, dict):
                    continue

                if 'inputs' in item:
                    inputs = dict[str, Any](item.get('inputs', {}))
                    outputs = dict[str, Any](
                        item.get('outputs', item.get('expected_outputs', {}))
                    )
                else:
                    # Flat JSON support
                    inputs = {}
                    outputs = {}
                    for key, value in item.items():
                        if key in ('expected_output', 'expected_outputs'):
                            outputs['expected_output'] = value
                        elif key != 'metadata':
                            inputs[key] = value

                if 'query' not in inputs:
                    raise InvalidDatasetError(
                        "Every test case must contain an 'inputs' object with a 'query' field.",
                    )

                test_cases.append(
                    TestCase(
                        id=uuid4(),
                        inputs=inputs,
                        expected_outputs=outputs,
                        metadata=item.get('metadata', {}),
                    ),
                )

        except json.JSONDecodeError as e:
            raise InvalidDatasetError('Invalid JSON file') from e

        return test_cases

    def _parse_csv(self, contents: bytes) -> list[TestCase]:
        """Parse a CSV file into test cases."""
        test_cases: list[TestCase] = []
        try:
            text = contents.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text))

            for row in reader:
                inputs: dict[str, Any] = {}
                outputs: dict[str, Any] = {}

                for key, value in row.items():
                    if key is None:
                        continue
                    if key == 'expected_output':
                        outputs[key] = value
                    else:
                        inputs[key] = value

                if 'query' not in inputs or not inputs['query'].strip():
                    raise InvalidDatasetError("CSV rows must contain a 'query' column.")

                test_cases.append(
                    TestCase(
                        id=uuid4(),
                        inputs=inputs,
                        expected_outputs=outputs,
                        metadata={},
                    ),
                )

        except Exception as e:
            raise InvalidDatasetError(f'Invalid CSV file: {str(e)}') from e

        return test_cases
