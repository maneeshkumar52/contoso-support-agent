"""Document indexing pipeline for Azure AI Search."""
import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import List
import structlog

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticSearch,
    SemanticPrioritizedFields, SemanticField,
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

from shared.config import get_settings
from shared.logging_config import configure_logging
from knowledge_base.chunker import RecursiveTextChunker

configure_logging()
logger = structlog.get_logger(__name__)


def create_search_index(index_client: SearchIndexClient, index_name: str) -> None:
    """Create Azure AI Search index with vector and semantic configuration."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="source_file", type=SearchFieldDataType.String),
        SimpleField(name="clearance_level", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="myHnswProfile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")],
    )

    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
        ),
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
    )

    try:
        index_client.create_or_update_index(index)
        logger.info("search_index_created", index_name=index_name)
    except Exception as exc:
        logger.error("search_index_creation_failed", error=str(exc))
        raise


def get_embedding(client: AzureOpenAI, text: str, deployment: str) -> List[float]:
    """Generate embedding for text."""
    response = client.embeddings.create(input=text, model=deployment)
    return response.data[0].embedding


def index_documents(documents_dir: str = None) -> None:
    """Main indexing pipeline."""
    settings = get_settings()

    if documents_dir is None:
        documents_dir = Path(__file__).parent / "documents"
    else:
        documents_dir = Path(documents_dir)

    openai_client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    credential = AzureKeyCredential(settings.azure_search_api_key)
    index_client = SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=credential)
    search_client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=credential,
    )

    create_search_index(index_client, settings.azure_search_index_name)
    chunker = RecursiveTextChunker(chunk_size=1000, chunk_overlap=200)

    md_files = list(documents_dir.glob("*.md"))
    logger.info("indexing_started", num_files=len(md_files))

    documents_to_index = []

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        title = md_file.stem.replace("_", " ").title()
        chunks = chunker.chunk_document(
            text=text,
            source_file=md_file.name,
            title=title,
            category="banking_policy",
            clearance_level="general",
        )

        for chunk in chunks:
            embedding = get_embedding(openai_client, chunk.content, settings.azure_openai_embedding_deployment)
            doc = {
                "id": str(uuid.uuid4()),
                "title": chunk.title,
                "content": chunk.content,
                "category": chunk.category,
                "source_file": chunk.source_file,
                "clearance_level": chunk.clearance_level,
                "chunk_index": chunk.chunk_index,
                "content_vector": embedding,
            }
            documents_to_index.append(doc)

    if documents_to_index:
        batch_size = 100
        for i in range(0, len(documents_to_index), batch_size):
            batch = documents_to_index[i:i + batch_size]
            search_client.upload_documents(documents=batch)
            logger.info("batch_indexed", batch_num=i // batch_size + 1, size=len(batch))

    logger.info("indexing_complete", total_chunks=len(documents_to_index))


if __name__ == "__main__":
    index_documents()
