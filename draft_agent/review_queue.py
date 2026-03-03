"""Human review queue integration using Cosmos DB."""
import uuid
from datetime import datetime
from typing import Dict, Any
import structlog

from shared.azure_clients import AzureClients
from shared.config import get_settings

logger = structlog.get_logger(__name__)


class ReviewQueue:
    """Manages the human review queue in Cosmos DB."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def push(self, customer_id: str, session_id: str, draft_data: Dict[str, Any]) -> str:
        """
        Push a draft response to the human review queue.

        Args:
            customer_id: Customer identifier.
            session_id: Session identifier.
            draft_data: Draft response and review notes.

        Returns:
            Review item ID.
        """
        review_id = str(uuid.uuid4())
        review_item = {
            "id": review_id,
            "customer_id": customer_id,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending_review",
            "draft_response": draft_data.get("draft_response", ""),
            "review_notes": draft_data.get("review_notes", ""),
            "priority": draft_data.get("priority", "normal"),
            "suggested_actions": draft_data.get("suggested_actions", []),
        }

        try:
            cosmos_client = AzureClients.get_cosmos_client()
            async with cosmos_client:
                db = cosmos_client.get_database_client(self.settings.cosmos_database)
                container = db.get_container_client(self.settings.cosmos_review_container)
                await container.create_item(body=review_item)
                logger.info("review_item_queued", review_id=review_id, customer_id=customer_id)
        except Exception as exc:
            logger.error("review_queue_push_failed", error=str(exc), review_id=review_id)
            # Continue even if Cosmos write fails — draft was still created

        return review_id
