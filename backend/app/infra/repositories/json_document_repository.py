import contextlib
from pathlib import Path

from app.core.documents.models import DocumentMetadata
from app.core.documents.ports import DocumentRepository
from pydantic import TypeAdapter, ValidationError


class LocalJsonDocumentRepository(DocumentRepository):
    """Local JSON implementation for DocumentRepository."""

    def __init__(self, uploads_dir: str | Path) -> None:
        self.uploads_dir = Path(uploads_dir)
        self.uploads_dir.parent.mkdir(parents=True, exist_ok=True)
        self.__ta = TypeAdapter(DocumentMetadata)

    def _get_path(self, document_id: str) -> Path:
        return self.uploads_dir / f'{document_id}.json'

    def find_by_id(self, document_id: str) -> DocumentMetadata | None:
        path = self._get_path(document_id)
        if not path.exists() or not path.is_file():
            return None

        raw_data = path.read_text(encoding='utf-8')

        try:
            return self.__ta.validate_json(raw_data)
        except ValidationError:
            return None

    def list_all(self) -> list[DocumentMetadata]:
        docs: list[DocumentMetadata] = []
        if not self.uploads_dir.exists():
            return docs

        for f in self.uploads_dir.glob('*.json'):
            raw_data = f.read_text(encoding='utf-8')
            with contextlib.suppress(ValidationError):
                docs.append(self.__ta.validate_json(raw_data))
        return docs

    def save(self, document: DocumentMetadata) -> None:
        path = self._get_path(document.id)
        path.write_bytes(self.__ta.dump_json(document))

    def delete(self, document_id: str) -> None:
        path = self._get_path(document_id)
        path.unlink(missing_ok=True)
