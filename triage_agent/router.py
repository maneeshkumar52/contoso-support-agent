"""Routing logic based on triage tier."""
import structlog
from shared.models import TriageResult, Tier, CustomerQuery

logger = structlog.get_logger(__name__)

# Confidence threshold below which we escalate to the next tier
CONFIDENCE_THRESHOLD = 0.7


def determine_route(triage_result: TriageResult, query: CustomerQuery) -> dict:
    """
    Determine the routing action based on triage result.

    Args:
        triage_result: The classification result from the triage agent.
        query: The original customer query.

    Returns:
        Dict with routing instructions.
    """
    effective_tier = triage_result.tier

    # If confidence is below threshold, escalate to next tier
    if triage_result.confidence < CONFIDENCE_THRESHOLD:
        if effective_tier == Tier.TIER_1:
            effective_tier = Tier.TIER_2
            logger.info(
                "tier_escalated_low_confidence",
                from_tier=1,
                to_tier=2,
                confidence=triage_result.confidence,
            )
        elif effective_tier == Tier.TIER_2:
            effective_tier = Tier.TIER_3
            logger.info(
                "tier_escalated_low_confidence",
                from_tier=2,
                to_tier=3,
                confidence=triage_result.confidence,
            )

    route_map = {
        Tier.TIER_1: {
            "agent": "resolution",
            "mode": "auto_resolve",
            "action": triage_result.auto_resolve_action,
            "description": "Auto-resolve common issue",
        },
        Tier.TIER_2: {
            "agent": "resolution",
            "mode": "rag_assisted",
            "action": None,
            "description": "RAG-assisted resolution",
        },
        Tier.TIER_3: {
            "agent": "draft",
            "mode": "human_review",
            "action": None,
            "description": "Human escalation required",
        },
    }

    route = route_map[effective_tier]
    route["effective_tier"] = effective_tier
    route["original_tier"] = triage_result.tier

    logger.info(
        "route_determined",
        effective_tier=effective_tier.value,
        agent=route["agent"],
        mode=route["mode"],
    )

    return route
