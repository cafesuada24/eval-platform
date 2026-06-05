from typing import Any

from pydantic import BaseModel, Field, field_validator


class DatasetSchemaDef(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)


class DatasetCreate(BaseModel):
    name: str
    schema_: DatasetSchemaDef = Field(default_factory=DatasetSchemaDef, alias="schema")

class DatasetUpdate(BaseModel):
    name: str
    schema_: DatasetSchemaDef = Field(default_factory=DatasetSchemaDef, alias="schema")

class TestCaseCreate(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('inputs')
    @classmethod
    def validate_inputs(cls, v: dict[str, Any]) -> dict[str, Any]:
        if 'query' not in v:
            raise ValueError("inputs must contain a 'query' field")
        return v

class TestCaseUpdate(TestCaseCreate):
    pass
