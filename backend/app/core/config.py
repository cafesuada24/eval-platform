"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Project directories
    # Default to the backend directory's fixtures folder (relative to this config file)
    fixtures_dir: Path = Path(__file__).resolve().parent.parent.parent / 'fixtures'

    # API Keys
    google_api_key: str | None = None

    # RAG parameters
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 3

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    @property
    def metrics_dir(self) -> Path:
        return self.fixtures_dir / 'metrics'

    @property
    def pipelines_dir(self) -> Path:
        return self.fixtures_dir / 'pipelines'

    @property
    def runtimes_dir(self) -> Path:
        return self.fixtures_dir / 'runtimes'

    @property
    def sessions_dir(self) -> Path:
        return self.fixtures_dir / 'sessions'

    @property
    def uploads_dir(self) -> Path:
        return self.fixtures_dir / 'uploads'

    @property
    def chromadb_dir(self) -> Path:
        return self.fixtures_dir / 'chromadb'

    @property
    def datasets_dir(self) -> Path:
        return self.fixtures_dir / 'datasets'

    @property
    def dataset_files_dir(self) -> Path:
        return self.fixtures_dir / 'dataset_files'

    @property
    def batch_results_dir(self) -> Path:
        return self.fixtures_dir / 'batch_results'


# Global settings instance
settings = Settings()
