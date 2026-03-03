"""Resolution Agent FastAPI entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from shared.logging_config import configure_logging
from shared.middleware import TracingMiddleware
from shared.models import CustomerQuery
from resolution_agent.agent import ResolutionAgent

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("resolution_agent_starting")
    yield
    logger.info("resolution_agent_stopping")


app = FastAPI(
    title="Contoso Resolution Agent",
    description="RAG-based resolution with tool calling",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(TracingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_agent = ResolutionAgent()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "resolution-agent"}


@app.post("/api/v1/resolve")
async def resolve_query(query: CustomerQuery, auto_resolve: bool = False, category: str = None):
    try:
        result = await _agent.resolve(query, auto_resolve=auto_resolve, category=category)
        return result.model_dump()
    except Exception as exc:
        logger.error("resolution_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
