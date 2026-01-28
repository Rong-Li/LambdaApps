"""Configuration module for homeapp service."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class MongoSettings(BaseSettings):
    """MongoDB settings loaded from environment variables."""

    mongodb_uri: str
    mongodb_database: str = 'homeapp'

    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8'}


class S3Settings(BaseSettings):
    """S3 settings loaded from environment variables."""

    s3_bucket_name: str = 'homeapp-archive'

    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8'}


@lru_cache
def get_mongo_settings() -> MongoSettings:
    """Get cached MongoDB settings instance."""
    return MongoSettings()


@lru_cache
def get_s3_settings() -> S3Settings:
    """Get cached S3 settings instance."""
    return S3Settings()
