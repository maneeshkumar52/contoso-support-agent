"""Triage Agent FastAPI entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from shared.logging_config import configure_logging
from shared.middleware import TracingMiddleware
from shared.models import CustomerQuery, TriageResult
from triage_agent.agent import TriageAgent
from triage_agent.router import determine_route

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("triage_agent_starting")
    yield
    logger.info("triage_agent_stopping")


app = FastAPI(
    title="Contoso Triage Agent",
    description="Classifies customer queries into support tiers",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(TracingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_agent = TriageAgent()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "triage-agent"}


@app.post("/api/v1/triage", response_model=dict)
async def triage_query(query: CustomerQuery) -> dict:
    """Classify a customer query and determine routing."""
    try:
        result = await _agent.classify(query)
        route = determine_route(result, query)
        return {
            "triage_result": result.model_dump(),
            "route": {k: str(v) if hasattr(v, 'value') else v for k, v in route.items()},
        }
    except Exception as exc:
        logger.error("triage_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
