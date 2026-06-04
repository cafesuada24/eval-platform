"""Dataset parser service."""

import csv
import io
import json
from uuid import uuid4

from app.core.eval_engine.models import Dataset, TestCase
from app.core.exceptions import DomainError


class InvalidDatasetError(DomainError):
    """Raised when a dataset file is invalid."""


class DatasetParserService:
    """Service to parse dataset files into Dataset entities."""

    def parse(self, filename: str, contents: bytes) -> Dataset:
        """Parse a dataset from bytes."""
        test_cases: list[TestCase] = []

        if filename.endswith('.json'):
            try:
                data = json.loads(contents.decode('utf-8'))
                if not isinstance(data, list):
                    raise InvalidDatasetError('JSON must be a list of test cases')
                for item in data:
                    test_cases.append(
                        TestCase(
                            id=uuid4(),
                            input_text=item.get('input_text', ''),
                            input_files=item.get('input_files', []),
                            expected_output=item.get('expected_output'),
                            metadata=item.get('metadata', {}),
                        )
                    )
            except json.JSONDecodeError as e:
                raise InvalidDatasetError('Invalid JSON file') from e

        elif filename.endswith('.csv'):
            try:
                text = contents.decode('utf-8')
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    test_cases.append(
                        TestCase(
                            id=uuid4(),
                            input_text=row.get('input_text', ''),
                            input_files=row.get('input_files', '').split(',')
                            if row.get('input_files')
                            else [],
                            expected_output=row.get('expected_output'),
                            metadata=row,
                        )
                    )
            except Exception as e:
                raise InvalidDatasetError(f'Invalid CSV file: {str(e)}') from e
        else:
            raise InvalidDatasetError('Only .json and .csv files are supported')

        return Dataset(
            id=uuid4(),
            name=filename,
            cases=test_cases,
        )
