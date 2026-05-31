from pydantic import BaseModel

class DocumentMetadata(BaseModel):
    id: str
    name: str
    text: str
    size: int
