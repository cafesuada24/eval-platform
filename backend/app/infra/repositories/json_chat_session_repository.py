from pathlib import Path
from uuid import UUID

from app.core.agents.metric_helper.models import ChatSession
from pydantic import TypeAdapter, ValidationError


class LocalJsonChatSessionRepository:
    """Local JSON implementation for ChatSessionRepository."""

    def __init__(self, sessions_dir: str | Path) -> None:
        self.__sessions_dir = Path(sessions_dir)
        self.__sessions_dir.parent.mkdir(exist_ok=True, parents=True)
        self.__ta = TypeAdapter(ChatSession)

    def _get_path(self, metric_id: UUID) -> Path:
        return self.__sessions_dir / f'{metric_id}.json'

    def find_by_id(self, metric_id: UUID) -> ChatSession | None:
        """Find a session by metric id."""
        path = self._get_path(metric_id)
        if not path.exists() or not path.is_file():
            return None
        try:
            raw_data = path.read_text(encoding='utf-8')
            return self.__ta.validate_json(raw_data)
        except ValidationError:
            return None

    def save(self, session: ChatSession) -> None:
        """Save a session."""
        path = self._get_path(session.metric_id)
        path.write_bytes(self.__ta.dump_json(session))

    def delete(self, metric_id: UUID) -> None:
        """Delete a session."""
        path = self._get_path(metric_id)
        path.unlink(missing_ok=True)
