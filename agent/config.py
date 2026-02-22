"""Agent configuration — all external endpoints and tuning knobs."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "AGENT_"}

    # LLM
    llm_provider: str = "openai"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.1

    # Observability backends
    prometheus_url: str = "http://prometheus:9090"
    loki_url: str = "http://loki:3100"
    tempo_url: str = "http://tempo:3200"

    # Knowledge base
    knowledge_dir: str = "/opt/agent/knowledge/runbooks"
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # Redis
    redis_url: str = "redis://redis:6379/0"
    dedup_window_seconds: int = 300
    max_concurrent_investigations: int = 3
    investigation_timeout_seconds: int = 600

    # Investigation tuning
    max_investigation_iterations: int = 6
    confidence_threshold: float = 0.7
    query_lookback_minutes: int = 30
    query_lookahead_minutes: int = 10

    # Agent server
    host: str = "0.0.0.0"
    port: int = 8100


settings = Settings()
