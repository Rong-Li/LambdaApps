"""Configuration module for homeapp service."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class MongoSettings(BaseSettings):
    """MongoDB settings loaded from environment variables."""

    host: str
    username: str
    password: SecretStr
    database: str = 'homeapp'
    check_create_index: bool = True

    model_config = {'env_prefix': 'MONGO_', 'env_file': '.env', 'env_file_encoding': 'utf-8', 'extra': 'ignore'}

    @property
    def mongo_uri(self) -> str:
        """Construct MongoDB URI from components."""
        return f'mongodb+srv://{self.username}:{self.password.get_secret_value()}@{self.host}'


class S3Settings(BaseSettings):
    """S3 settings loaded from environment variables."""

    bucket_name: str = 'rong-li-bucket'

    model_config = {'env_prefix': 'S3_', 'env_file': '.env', 'env_file_encoding': 'utf-8', 'extra': 'ignore'}


@lru_cache
def get_mongo_settings() -> MongoSettings:
    """Get cached MongoDB settings instance."""
    return MongoSettings()


@lru_cache
def get_s3_settings() -> S3Settings:
    """Get cached S3 settings instance."""
    return S3Settings()


class AuthSettings(BaseSettings):
    """Authentication settings loaded from environment variables."""

    bearer_token: str = ''  # Comma-separated list of valid tokens

    model_config = {'env_prefix': 'AUTH_', 'env_file': '.env', 'env_file_encoding': 'utf-8', 'extra': 'ignore'}

    @property
    def bearer_tokens(self) -> list[str]:
        """Return list of valid bearer tokens (supports comma-separated values)."""
        if not self.bearer_token:
            return []
        return [t.strip() for t in self.bearer_token.split(',') if t.strip()]


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Get cached Auth settings instance."""
    return AuthSettings()
