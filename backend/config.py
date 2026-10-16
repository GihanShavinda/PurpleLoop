from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://purpleforge_user:CHANGE_ME@127.0.0.1:5432/purpleforge'
    redis_url: str = 'redis://127.0.0.1:6379/0'
    neo4j_uri: str = 'bolt://127.0.0.1:7687'
    neo4j_username: str = 'neo4j'
    neo4j_password: str = 'CHANGE_ME'
    jwt_secret: str = Field(default='REPLACE_WITH_AT_LEAST_32_RANDOM_CHARACTERS', min_length=32)
    jwt_algorithm: str = 'HS256'
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    frontend_url: str = 'http://localhost:4200'
    cors_origins: str = 'http://localhost:4200'
    log_level: str = 'INFO'
    admin_email: str = 'admin@purpleforge.local'
    admin_password: str = 'CHANGE_ME_BEFORE_SEEDING'

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

@lru_cache
def get_settings():
    return Settings()
