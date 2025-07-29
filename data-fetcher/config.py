"""
Simple configuration management using Pydantic
"""
from pydantic_settings import BaseSettings
from typing import Optional


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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()