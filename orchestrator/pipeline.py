"""Main orchestration pipeline: triage -> resolution/draft -> audit -> respond."""
import time
import uuid
from typing import Optional
import structlog

from shared.models import (
    CustomerQuery, TriageResult, ResolutionResult,
    DraftResult, AuditRecord, PipelineResult, Tier,
)
from shared.azure_clients import AzureClients
from shared.config import get_settings
from triage_agent.agent import TriageAgent
from triage_agent.router import determine_route
from resolution_agent.agent import ResolutionAgent
from draft_agent.agent import DraftAgent
from orchestrator.escalation import handle_escalation

logger = structlog.get_logger(__name__)


class SupportPipeline:
    """Orchestrates the full customer support pipeline."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.triage_agent = TriageAgent()
        self.resolution_agent = ResolutionAgent()
        self.draft_agent = DraftAgent()

    async def _write_audit(self, record: AuditRecord) -> None:
        """Write audit record to Cosmos DB."""
        try:
            cosmos_client = AzureClients.get_cosmos_client()
            async with cosmos_client:
                db = cosmos_client.get_database_client(self.settings.cosmos_database)
                container = db.get_container_client(self.settings.cosmos_container)
                doc = record.model_dump()
                doc["timestamp"] = doc["timestamp"].isoformat()
                doc["tier"] = record.tier
                await container.create_item(body=doc)
                logger.info("audit_record_written", audit_id=record.id)
        except Exception as exc:
            logger.error("audit_write_failed", error=str(exc), audit_id=record.id)

    async def run(self, query: CustomerQuery) -> PipelineResult:
        """
        Execute the full support pipeline.

        Args:
            query: The incoming customer query.

        Returns:
            PipelineResult with response, tier, agents used, and timing.
        """
        pipeline_start = time.time()
        agents_used = []
        audit_id = str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(
            customer_id=query.customer_id,
            session_id=query.session_id,
            correlation_id=query.correlation_id,
        )

        logger.info("pipeline_started", customer_id=query.customer_id)

        try:
            # Phase 1: Triage
            stage_start = time.time()
            triage_result = await self.triage_agent.classify(query)
            agents_used.append("triage_agent")
            logger.info("triage_stage_complete", latency_ms=round((time.time() - stage_start) * 1000, 2))

            # Phase 2: Route
            route = determine_route(triage_result, query)
            effective_tier = route["effective_tier"]

            final_response = ""
            sources = []

            # Phase 3: Resolve or Draft
            if route["agent"] == "resolution":
                stage_start = time.time()
                resolution = await self.resolution_agent.resolve(
                    query=query,
                    auto_resolve=(route["mode"] == "auto_resolve"),
                    auto_resolve_action=route.get("action"),
                    category=triage_result.category,
                )
                agents_used.append("resolution_agent")
                final_response = resolution.answer
                sources = resolution.sources
                logger.info("resolution_stage_complete", latency_ms=round((time.time() - stage_start) * 1000, 2))

            elif route["agent"] == "draft":
                stage_start = time.time()
                draft = await self.draft_agent.draft(query=query, category=triage_result.category)
                escalation = await handle_escalation(query, draft)
                agents_used.extend(["draft_agent", "escalation_handler"])
                # For Tier 3, send the escalation message to customer
                final_response = escalation["customer_message"]
                logger.info("draft_stage_complete", latency_ms=round((time.time() - stage_start) * 1000, 2))

            total_latency_ms = (time.time() - pipeline_start) * 1000

            # Phase 4: Audit
            audit_record = AuditRecord(
                id=audit_id,
                customer_id=query.customer_id,
                session_id=query.session_id,
                correlation_id=query.correlation_id,
                query=query.message,
                response=final_response,
                tier=effective_tier.value,
                agent_chain=agents_used,
                latency_ms=round(total_latency_ms, 2),
                channel=query.channel.value,
            )
            await self._write_audit(audit_record)

            logger.info(
                "pipeline_complete",
                total_latency_ms=round(total_latency_ms, 2),
                tier=effective_tier.value,
                agents=agents_used,
            )

            return PipelineResult(
                final_response=final_response,
                tier=effective_tier,
                agents_used=agents_used,
                total_latency_ms=round(total_latency_ms, 2),
                audit_id=audit_id,
                session_id=query.session_id,
                sources=sources,
            )

        except Exception as exc:
            total_latency_ms = (time.time() - pipeline_start) * 1000
            logger.error("pipeline_failed", error=str(exc), latency_ms=round(total_latency_ms, 2))
            return PipelineResult(
                final_response="We apologise, but we're experiencing a temporary issue. Please try again or call us on 0800-CONTOSO.",
                tier=Tier.TIER_3,
                agents_used=agents_used,
                total_latency_ms=round(total_latency_ms, 2),
                audit_id=audit_id,
                session_id=query.session_id,
            )
