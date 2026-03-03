"""Draft Agent FastAPI entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from shared.logging_config import configure_logging
from shared.middleware import TracingMiddleware
from shared.models import CustomerQuery
from draft_agent.agent import DraftAgent

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("draft_agent_starting")
    yield
    logger.info("draft_agent_stopping")


app = FastAPI(title="Contoso Draft Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(TracingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_agent = DraftAgent()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "draft-agent"}


@app.post("/api/v1/draft")
async def draft_response(query: CustomerQuery, category: str = "general"):
    try:
        result = await _agent.draft(query, category=category)
        return result.model_dump()
    except Exception as exc:
        logger.error("draft_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
