"""Triage agent: classifies customer queries into Tier 1/2/3."""
import json
import structlog
from typing import Optional

from shared.azure_clients import AzureClients
from shared.config import get_settings
from shared.models import CustomerQuery, TriageResult, Tier
from triage_agent.prompts import TRIAGE_SYSTEM_PROMPT

logger = structlog.get_logger(__name__)


class TriageAgent:
    """Classifies incoming customer queries into support tiers."""

    def __init__(self) -> None:
        """Initialize the triage agent."""
        self.settings = get_settings()
        self.client = AzureClients.get_openai_client()

    async def classify(self, query: CustomerQuery) -> TriageResult:
        """
        Classify a customer query into Tier 1, 2, or 3.

        Args:
            query: The incoming customer query.

        Returns:
            TriageResult with tier, category, confidence, and reasoning.
        """
        logger.info(
            "triage_classification_started",
            customer_id=query.customer_id,
            session_id=query.session_id,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Customer query: {query.message}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=500,
            )

            raw_response = response.choices[0].message.content
            parsed = json.loads(raw_response)

            result = TriageResult(
                tier=Tier(parsed["tier"]),
                category=parsed["category"],
                confidence=float(parsed["confidence"]),
                reasoning=parsed["reasoning"],
                auto_resolve_action=parsed.get("auto_resolve_action"),
            )

            logger.info(
                "triage_classification_complete",
                tier=result.tier.value,
                category=result.category,
                confidence=result.confidence,
                customer_id=query.customer_id,
            )

            return result

        except Exception as exc:
            logger.error("triage_classification_failed", error=str(exc), customer_id=query.customer_id)
            # Default to Tier 2 on error (safe fallback)
            return TriageResult(
                tier=Tier.TIER_2,
                category="unknown",
                confidence=0.5,
                reasoning=f"Triage failed, defaulting to Tier 2: {str(exc)}",
            )
