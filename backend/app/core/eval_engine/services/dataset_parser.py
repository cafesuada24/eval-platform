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

    def parse(
        self,
        filename: str,
        contents: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> Dataset:
        """Parse a dataset from bytes.

        Args:
            filename: Name of the uploaded file.
            contents: Raw bytes of the file.
            column_mapping: Optional schema mapping dictionary.

        Returns:
            Parsed Dataset entity.

        Raises:
            InvalidDatasetError: If file format is unsupported or invalid.
        """
        if filename.endswith('.json'):
            test_cases = self._parse_json(contents, column_mapping)
        elif filename.endswith('.jsonl'):
            test_cases = self._parse_jsonl(contents, column_mapping)
        elif filename.endswith('.csv'):
            test_cases = self._parse_csv(contents, column_mapping)
        else:
            raise InvalidDatasetError('Only .json, .jsonl, and .csv files are supported')

        return Dataset(
            id=uuid4(),
            name=filename,
            cases=test_cases,
        )

    def _apply_mapping(
        self,
        item: dict[str, Any],
        column_mapping: dict[str, str] | None,
        is_csv: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Applies column mapping or parses using default behavior.

        Returns (inputs, expected_outputs, metadata)
        """
        if not column_mapping:
            # Fallback to default/legacy behavior
            if not is_csv and 'inputs' in item:
                inputs = dict[str, Any](item.get('inputs', {}))
                outputs = dict[str, Any](
                    item.get('outputs', item.get('expected_outputs', {}))
                )
                if 'expected_output' not in outputs:
                    for k in ('expected_outputs', 'output'):
                        if k in outputs:
                            outputs['expected_output'] = outputs[k]
                return inputs, outputs, dict[str, Any](item.get('metadata', {}))
            else:
                inputs = {}
                outputs = {}
                metadata = dict[str, Any](item.get('metadata', {})) if not is_csv else {}
                for key, value in item.items():
                    if key is None or key == 'metadata':
                        continue
                    if key in ('expected_output', 'expected_outputs', 'output'):
                        outputs['expected_output'] = value
                    else:
                        inputs[key] = value
                return inputs, outputs, metadata

        # If mapping is provided
        inputs = {}
        outputs = {}
        metadata = {}

        flat_item: dict[str, Any] = {}

        def flatten(d: dict[str, Any], prefix: str = ""):
            for k, v in d.items():
                flat_key = f"{prefix}{k}"
                if isinstance(v, dict) and k != 'metadata':
                    flatten(v, f"{flat_key}.")
                else:
                    flat_item[flat_key] = v

        if not is_csv and ('inputs' in item or 'outputs' in item or 'expected_outputs' in item):
            flatten(item)
        else:
            flat_item = item.copy()
            if 'metadata' in flat_item and isinstance(flat_item['metadata'], dict):
                metadata = flat_item.pop('metadata').copy()

        for src_key, val in flat_item.items():
            if src_key in column_mapping:
                target = column_mapping[src_key]
                if target == 'query':
                    inputs['query'] = val
                elif target == 'expected_output':
                    outputs['expected_output'] = val
                elif target.startswith('metadata.'):
                    meta_key = target.split('.', 1)[1]
                    metadata[meta_key] = val
                elif target.startswith('inputs.'):
                    inputs_key = target.split('.', 1)[1]
                    inputs[inputs_key] = val
                elif target.startswith('expected_outputs.'):
                    outputs_key = target.split('.', 1)[1]
                    outputs[outputs_key] = val
            else:
                if src_key not in ('metadata', 'expected_output', 'expected_outputs', 'outputs', 'inputs'):
                    inputs[src_key] = val

        return inputs, outputs, metadata

    def _parse_json(
        self,
        contents: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> list[TestCase]:
        """Parse a JSON file into test cases."""
        test_cases: list[TestCase] = []
        try:
            data = json.loads(contents.decode('utf-8'))
            if not isinstance(data, list):
                raise InvalidDatasetError('JSON must be a list of test cases')

            for item in data:
                if not isinstance(item, dict):
                    continue

                inputs, expected_outputs, metadata = self._apply_mapping(
                    item, column_mapping, is_csv=False
                )

                if 'query' not in inputs:
                    raise InvalidDatasetError(
                        "Every test case must contain an 'inputs' object with a 'query' field.",
                    )

                test_cases.append(
                    TestCase(
                        id=uuid4(),
                        inputs=inputs,
                        expected_outputs=expected_outputs,
                        metadata=metadata,
                    ),
                )

        except json.JSONDecodeError as e:
            raise InvalidDatasetError('Invalid JSON file') from e

        return test_cases

    def _parse_jsonl(
        self,
        contents: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> list[TestCase]:
        """Parse a JSONL file into test cases."""
        test_cases: list[TestCase] = []
        try:
            text = contents.decode('utf-8')
            for line_idx, line in enumerate(text.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as e:
                    raise InvalidDatasetError(
                        f"Invalid JSON at line {line_idx}: {str(e)}"
                    ) from e

                if not isinstance(item, dict):
                    raise InvalidDatasetError(
                        f"Line {line_idx} in JSONL must be a JSON object"
                    )

                inputs, expected_outputs, metadata = self._apply_mapping(
                    item, column_mapping, is_csv=False
                )

                if 'query' not in inputs or not inputs['query'].strip():
                    raise InvalidDatasetError(
                        f"Line {line_idx} does not map to a 'query' field."
                    )

                test_cases.append(
                    TestCase(
                        id=uuid4(),
                        inputs=inputs,
                        expected_outputs=expected_outputs,
                        metadata=metadata,
                    ),
                )
        except InvalidDatasetError:
            raise
        except Exception as e:
            raise InvalidDatasetError(f"Invalid JSONL file: {str(e)}") from e

        return test_cases

    def _parse_csv(
        self,
        contents: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> list[TestCase]:
        """Parse a CSV file into test cases."""
        test_cases: list[TestCase] = []
        try:
            text = contents.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text))

            for row in reader:
                inputs, expected_outputs, metadata = self._apply_mapping(
                    row, column_mapping, is_csv=True
                )

                if 'query' not in inputs or not inputs['query'].strip():
                    raise InvalidDatasetError("CSV rows must contain a 'query' column.")

                test_cases.append(
                    TestCase(
                        id=uuid4(),
                        inputs=inputs,
                        expected_outputs=expected_outputs,
                        metadata=metadata,
                    ),
                )

        except InvalidDatasetError:
            raise
        except Exception as e:
            raise InvalidDatasetError(f'Invalid CSV file: {str(e)}') from e

        return test_cases
