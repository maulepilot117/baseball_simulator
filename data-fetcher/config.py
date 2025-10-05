"""
Simple configuration management using Pydantic
"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "baseball_user"
    db_password: str = "baseball_pass"
    db_name: str = "baseball_sim"
    
    # API settings
    port: int = 8082
    fetch_interval: int = 86400  # 24 hours in seconds
    initial_years: int = 5  # Years of history to fetch on first run
    
    # MLB API settings
    mlb_api_base_url: str = "https://statsapi.mlb.com/api/v1"
    request_timeout: int = 30
    max_retries: int = 3

    # Security: Debug mode disabled by default, enable via environment variable
    debug: bool = False

    http_max_connections: int = 100
    http_keepalive_connections: int = 50

    skip_incomplete_games: bool = True
    fetch_spring_training: bool = False
    game_fetch_retry_on_404: bool = False
    
    # CORS settings
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()