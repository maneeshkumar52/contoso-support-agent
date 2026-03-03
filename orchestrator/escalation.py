"""Human escalation handler."""
import structlog
from shared.models import CustomerQuery, DraftResult

logger = structlog.get_logger(__name__)


async def handle_escalation(query: CustomerQuery, draft: DraftResult) -> dict:
    """
    Handle human escalation for Tier 3 cases.

    Args:
        query: Original customer query.
        draft: Draft response prepared by draft agent.

    Returns:
        Escalation confirmation dict.
    """
    logger.info(
        "human_escalation_triggered",
        customer_id=query.customer_id,
        priority=draft.priority,
        channel=query.channel.value,
    )

    # In production: integrate with CRM, ticketing system (e.g., Salesforce, Zendesk)
    escalation_data = {
        "status": "escalated_to_human",
        "customer_message": "Your request has been escalated to our specialist team. You will receive a response within 2 business hours.",
        "internal_reference": f"ESC-{query.session_id[:8].upper()}",
        "priority": draft.priority,
        "channel": query.channel.value,
    }

    logger.info("escalation_complete", reference=escalation_data["internal_reference"])
    return escalation_data
