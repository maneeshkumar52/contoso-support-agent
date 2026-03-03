"""Configuration and Azure client settings using pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str = Field(default="https://your-openai.openai.azure.com/", env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="your-api-key", env="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-02-01", env="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment: str = Field(default="gpt-4o", env="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-3-large", env="AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    # Azure AI Search
    azure_search_endpoint: str = Field(default="https://your-search.search.windows.net", env="AZURE_SEARCH_ENDPOINT")
    azure_search_api_key: str = Field(default="your-search-key", env="AZURE_SEARCH_API_KEY")
    azure_search_index_name: str = Field(default="contoso-knowledge-base", env="AZURE_SEARCH_INDEX_NAME")

    # Cosmos DB
    cosmos_endpoint: str = Field(default="https://your-cosmos.documents.azure.com:443/", env="COSMOS_ENDPOINT")
    cosmos_key: str = Field(default="your-cosmos-key", env="COSMOS_KEY")
    cosmos_database: str = Field(default="contoso-support", env="COSMOS_DATABASE")
    cosmos_container: str = Field(default="audit-records", env="COSMOS_CONTAINER")
    cosmos_review_container: str = Field(default="review-queue", env="COSMOS_REVIEW_CONTAINER")

    # Service URLs (for inter-agent communication)
    triage_agent_url: str = Field(default="http://localhost:8001", env="TRIAGE_AGENT_URL")
    resolution_agent_url: str = Field(default="http://localhost:8002", env="RESOLUTION_AGENT_URL")
    draft_agent_url: str = Field(default="http://localhost:8003", env="DRAFT_AGENT_URL")

    # App config
    app_name: str = "Contoso Support Agent"
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    use_managed_identity: bool = Field(default=False, env="USE_MANAGED_IDENTITY")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
