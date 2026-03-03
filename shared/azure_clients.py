"""Azure client singletons with retry policies."""
import asyncio
from functools import lru_cache
from typing import Optional
import structlog

from openai import AsyncAzureOpenAI
from azure.search.documents.aio import SearchClient
from azure.search.documents import SearchClient as SyncSearchClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey

from shared.config import get_settings

logger = structlog.get_logger(__name__)


class AzureClients:
    """Manages Azure service client singletons."""

    _openai_client: Optional[AsyncAzureOpenAI] = None
    _search_client: Optional[SearchClient] = None
    _cosmos_client: Optional[CosmosClient] = None

    @classmethod
    def get_openai_client(cls) -> AsyncAzureOpenAI:
        """Return singleton Azure OpenAI async client."""
        if cls._openai_client is None:
            settings = get_settings()
            cls._openai_client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                max_retries=3,
            )
            logger.info("azure_openai_client_initialized")
        return cls._openai_client

    @classmethod
    def get_search_client(cls) -> SearchClient:
        """Return singleton Azure AI Search async client."""
        if cls._search_client is None:
            settings = get_settings()
            cls._search_client = SearchClient(
                endpoint=settings.azure_search_endpoint,
                index_name=settings.azure_search_index_name,
                credential=AzureKeyCredential(settings.azure_search_api_key),
            )
            logger.info("azure_search_client_initialized")
        return cls._search_client

    @classmethod
    def get_cosmos_client(cls) -> CosmosClient:
        """Return singleton Cosmos DB async client."""
        if cls._cosmos_client is None:
            settings = get_settings()
            cls._cosmos_client = CosmosClient(
                url=settings.cosmos_endpoint,
                credential=settings.cosmos_key,
            )
            logger.info("cosmos_client_initialized")
        return cls._cosmos_client

    @classmethod
    async def close_all(cls) -> None:
        """Close all client connections."""
        if cls._openai_client:
            await cls._openai_client.close()
            cls._openai_client = None
        if cls._search_client:
            await cls._search_client.close()
            cls._search_client = None
        if cls._cosmos_client:
            await cls._cosmos_client.close()
            cls._cosmos_client = None
        logger.info("all_azure_clients_closed")
