"""Orchestrator FastAPI entry point — main API for the support system."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from shared.logging_config import configure_logging
from shared.middleware import TracingMiddleware
from shared.models import CustomerQuery, PipelineResult
from orchestrator.pipeline import SupportPipeline

configure_logging()
logger = structlog.get_logger(__name__)

pipeline: SupportPipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    pipeline = SupportPipeline()
    logger.info("orchestrator_starting")
    yield
    logger.info("orchestrator_stopping")


app = FastAPI(
    title="Contoso Support Orchestrator",
    description="Multi-agent customer support system for Contoso Financial Services",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(TracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "orchestrator", "version": "1.0.0"}


@app.post("/api/v1/query", response_model=dict)
async def handle_query(query: CustomerQuery) -> dict:
    """
    Main endpoint: receives a customer query and runs the full support pipeline.

    Returns a complete response with tier classification, agent chain, and final answer.
    """
    try:
        result = await pipeline.run(query)
        return result.model_dump()
    except Exception as exc:
        logger.error("orchestrator_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
