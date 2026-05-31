from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class RAGParameters(BaseModel):
    """Parameters for Retrieval-Augmented Generation."""
    chunk_size: int
    chunk_overlap: int
    top_k: int


@dataclass(slots=True)
class VectorDocument:
    """A document containing text and metadata."""
    id: str
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class QueryResult:
    """A single result from a vector query."""
    document: VectorDocument
    score: float
