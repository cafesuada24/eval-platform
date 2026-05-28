from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatSession(BaseModel):
    metric_name: str
    messages: list[ChatMessage]
