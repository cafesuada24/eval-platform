from pydantic import BaseModel

class UploadedFileMetadata(BaseModel):
    id: str
    name: str
    text: str
    size: int
