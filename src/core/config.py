"""Application configuration management."""

import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define the root directory
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def get_environment() -> Environment:
    """Get the current environment."""
    env_str = (os.getenv("ENVIRONMENT") or "development").lower()
    env_mapping = {
        "production": Environment.PRODUCTION,
        "prod": Environment.PRODUCTION,
        "staging": Environment.STAGING,
        "stage": Environment.STAGING,
        "test": Environment.TEST,
        "development": Environment.DEVELOPMENT,
        "dev": Environment.DEVELOPMENT,
    }
    return env_mapping.get(env_str, Environment.DEVELOPMENT)


def load_env_file():
    """Load environment-specific .env file."""
    env = get_environment()
    env_files = [
        ROOT_DIR / f".env.{env.value}.local",
        ROOT_DIR / f".env.{env.value}",
        ROOT_DIR / ".env.local",
        ROOT_DIR / ".env",
    ]
    for env_file in env_files:
        if env_file.is_file():
            load_dotenv(dotenv_path=env_file)
            return env_file
    return None


ENV_FILE = load_env_file()


class Settings(BaseSettings):
    """Settings for the RAG Service."""
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, 
        env_file_encoding="utf-8", 
        extra="ignore"
    )
    
    # Environment
    ENVIRONMENT: Environment = Field(default_factory=get_environment)
    
    # Application Settings
    PROJECT_NAME: str
    VERSION: str
    DESCRIPTION: str
    API_V1_STR: str
    HOST: str
    PORT: int
    DEBUG: bool
    
    # CORS Settings
    ALLOWED_ORIGINS: list[str]
    
    # PostgreSQL Settings (for PGVector)
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DATABASE: str
    
    # Neo4j Settings
    NEO4J_URI: str
    NEO4J_DATABASE: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    
    # LiteLLM Proxy
    LITELLM_URL: str
    LITELLM_KEY: str
    
    # LLM and Embedding Settings
    OPENAI_API_KEY: str
    LLM_MODEL: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIM: int
    
    # Directory Settings
    WORKING_DIR: str
    SCHEMA_DOCS_DIR: str
    DATA_DIR: str
    
    # Logging Configuration
    LOG_DIR: Path
    LOG_LEVEL: str
    APPLICATION_LOG_LEVEL: str
    LOG_FORMAT: str
    
    # LightRAG Settings
    MAX_ASYNC: int
    MAX_TOKENS: int
    MAX_EMBED_TOKENS: int
    
    # Query Settings
    TOP_K: int
    
    @model_validator(mode="after")
    def _apply_environment_settings(self) -> "Settings":
        """Apply environment-specific default settings."""
        env_settings = {
            Environment.DEVELOPMENT: {
                "DEBUG": True,
                "LOG_LEVEL": "WARNING",
                "APPLICATION_LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
            },
            Environment.PRODUCTION: {
                "DEBUG": False,
                "LOG_LEVEL": "WARNING",
                "APPLICATION_LOG_LEVEL": "INFO",
                "LOG_FORMAT": "json",
            },
        }
        current_env_settings = env_settings.get(self.ENVIRONMENT, {})
        for key, value in current_env_settings.items():
            if key not in self.model_fields_set:
                setattr(self, key, value)
        return self
    
    @model_validator(mode="after")
    def _construct_absolute_paths(self) -> "Settings":
        """Construct absolute paths for directories."""
        if not Path(self.WORKING_DIR).is_absolute():
            self.WORKING_DIR = str(ROOT_DIR / self.WORKING_DIR)
        if not Path(self.SCHEMA_DOCS_DIR).is_absolute():
            self.SCHEMA_DOCS_DIR = str(ROOT_DIR / self.SCHEMA_DOCS_DIR)
        if not Path(self.DATA_DIR).is_absolute():
            self.DATA_DIR = str(ROOT_DIR / self.DATA_DIR)
        return self
    
    @property
    def postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"


settings = Settings()

