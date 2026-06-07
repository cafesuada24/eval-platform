from typing import Any

from pydantic import BaseModel, Field


class DatasetSchemaDef(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    schema_: DatasetSchemaDef = Field(default_factory=DatasetSchemaDef, alias="schema")

class DatasetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    schema_: DatasetSchemaDef | None = Field(default=None, alias="schema")

class TestCaseCreate(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class TestCaseUpdate(TestCaseCreate):
    pass
