from typing import Optional
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    env: str = "development"
    debug: bool = True
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Database Configuration
    persistence_enabled: bool = True
    wal_directory: Path = Path("./data/wal")
    snapshot_directory: Path = Path("./data/snapshots")
    index_directory: Path = Path("./data/indexes")
    
    # Index Configuration
    default_index_type: str = "HNSW"
    lsh_tables: int = 10
    lsh_key_size: int = 10
    hnsw_m: int = 16
    hnsw_ef_construction: int = 200
    
    # Performance Configuration
    max_workers: int = 4
    batch_size: int = 1000
    cache_size: int = 10000
    cache_ttl: int = 3600
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [self.wal_directory, self.snapshot_directory, self.index_directory]:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
