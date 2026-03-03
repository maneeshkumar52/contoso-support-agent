"""Azure AI Search hybrid retrieval for the resolution agent."""
import structlog
from typing import List, Optional

from azure.search.documents.models import VectorizedQuery
from shared.azure_clients import AzureClients
from shared.config import get_settings
from shared.models import RetrievedDocument

logger = structlog.get_logger(__name__)


class HybridRetriever:
    """Performs hybrid (vector + keyword) retrieval from Azure AI Search."""

    def __init__(self) -> None:
        """Initialize the retriever."""
        self.settings = get_settings()
        self.openai_client = AzureClients.get_openai_client()
        self.search_client = AzureClients.get_search_client()

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a query text."""
        try:
            response = await self.openai_client.embeddings.create(
                input=text,
                model=self.settings.azure_openai_embedding_deployment,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("embedding_generation_failed", error=str(exc))
            return []

    async def search(
        self,
        query: str,
        category_filter: Optional[str] = None,
        top_k: int = 5,
    ) -> List[RetrievedDocument]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            query: The search query text.
            category_filter: Optional category to filter results.
            top_k: Number of top results to return.

        Returns:
            List of retrieved documents with relevance scores.
        """
        logger.info("hybrid_search_started", query=query[:100], category=category_filter)

        try:
            embedding = await self._get_embedding(query)

            search_kwargs = {
                "search_text": query,
                "top": top_k,
                "select": ["title", "content", "category", "source_url"],
                "query_type": "semantic",
                "semantic_configuration_name": "default",
            }

            if embedding:
                vector_query = VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=top_k,
                    fields="content_vector",
                )
                search_kwargs["vector_queries"] = [vector_query]

            if category_filter:
                search_kwargs["filter"] = f"category eq '{category_filter}'"

            results = []
            async with self.search_client as client:
                async for doc in await client.search(**search_kwargs):
                    results.append(
                        RetrievedDocument(
                            title=doc.get("title", "Unknown"),
                            content=doc.get("content", ""),
                            relevance_score=doc.get("@search.score", 0.0),
                            source_url=doc.get("source_url"),
                            category=doc.get("category"),
                        )
                    )

            logger.info("hybrid_search_complete", num_results=len(results))
            return results

        except Exception as exc:
            logger.error("hybrid_search_failed", error=str(exc))
            # Return empty list on search failure - agent will handle gracefully
            return []
