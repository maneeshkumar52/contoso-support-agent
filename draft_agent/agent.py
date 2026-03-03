"""Draft agent: generates draft responses for human review."""
import json
import structlog
from shared.azure_clients import AzureClients
from shared.config import get_settings
from shared.models import CustomerQuery, DraftResult, Tier
from draft_agent.prompts import DRAFT_SYSTEM_PROMPT
from draft_agent.review_queue import ReviewQueue

logger = structlog.get_logger(__name__)


class DraftAgent:
    """Generates professional draft responses for Tier 3 human review cases."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AzureClients.get_openai_client()
        self.review_queue = ReviewQueue()

    async def draft(self, query: CustomerQuery, category: str = "general") -> DraftResult:
        """
        Generate a draft response and queue for human review.

        Args:
            query: The customer's query.
            category: Query category from triage.

        Returns:
            DraftResult with draft response, review notes, and queue ID.
        """
        logger.info(
            "draft_generation_started",
            customer_id=query.customer_id,
            category=category,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Customer ID: {query.customer_id}\n"
                            f"Channel: {query.channel}\n"
                            f"Category: {category}\n"
                            f"Customer Message: {query.message}\n\n"
                            "Please draft a response for human review."
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=1000,
            )

            parsed = json.loads(response.choices[0].message.content)

            # Push to review queue
            await self.review_queue.push(
                customer_id=query.customer_id,
                session_id=query.session_id,
                draft_data=parsed,
            )

            result = DraftResult(
                draft_response=parsed.get("draft_response", ""),
                review_notes=parsed.get("review_notes", ""),
                priority=parsed.get("priority", "normal"),
                suggested_tier=Tier.TIER_3,
            )

            logger.info(
                "draft_generation_complete",
                customer_id=query.customer_id,
                priority=result.priority,
            )

            return result

        except Exception as exc:
            logger.error("draft_generation_failed", error=str(exc))
            return DraftResult(
                draft_response="Thank you for contacting Contoso Financial Services. We have received your query and a member of our team will be in touch within 24 hours.",
                review_notes=f"Auto-draft failed due to error: {str(exc)}. Please review the original query manually.",
                priority="high",
            )
