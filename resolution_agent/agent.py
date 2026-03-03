"""Resolution agent: RAG-based resolution with tool calling."""
import json
import time
from typing import List, Optional
import structlog

from shared.azure_clients import AzureClients
from shared.config import get_settings
from shared.models import CustomerQuery, RetrievedDocument, ResolutionResult, ToolCall
from resolution_agent.prompts import RESOLUTION_SYSTEM_PROMPT, AUTO_RESOLVE_PROMPT
from resolution_agent.retriever import HybridRetriever
from resolution_agent.tools import TOOL_DEFINITIONS, TOOL_HANDLERS

logger = structlog.get_logger(__name__)

MAX_TOOL_ITERATIONS = 3


class ResolutionAgent:
    """Resolves customer queries using RAG and tool calling."""

    def __init__(self) -> None:
        """Initialize the resolution agent."""
        self.settings = get_settings()
        self.client = AzureClients.get_openai_client()
        self.retriever = HybridRetriever()

    async def resolve(
        self,
        query: CustomerQuery,
        auto_resolve: bool = False,
        auto_resolve_action: Optional[str] = None,
        category: Optional[str] = None,
    ) -> ResolutionResult:
        """
        Resolve a customer query using RAG and tool calling.

        Args:
            query: The customer's query.
            auto_resolve: Whether to auto-resolve a Tier 1 issue.
            auto_resolve_action: Specific action for auto-resolve.
            category: Query category for targeted retrieval.

        Returns:
            ResolutionResult with answer, sources, and tool calls made.
        """
        start_time = time.time()
        tool_calls_made: List[ToolCall] = []
        total_tokens = 0

        logger.info(
            "resolution_started",
            customer_id=query.customer_id,
            auto_resolve=auto_resolve,
            category=category,
        )

        # Retrieve relevant documents
        retrieved_docs: List[RetrievedDocument] = []
        if not auto_resolve:
            retrieved_docs = await self.retriever.search(
                query=query.message,
                category_filter=category,
                top_k=5,
            )

        # Build context from retrieved documents
        context_text = ""
        sources = []
        for i, doc in enumerate(retrieved_docs):
            context_text += f"\n[Document {i+1}: {doc.title}]\n{doc.content}\n"
            sources.append(doc.title)

        # Choose system prompt
        system_prompt = AUTO_RESOLVE_PROMPT if auto_resolve else RESOLUTION_SYSTEM_PROMPT

        # Build initial messages
        user_content = query.message
        if context_text:
            user_content = f"Customer Query: {query.message}\n\nRelevant Knowledge Base:\n{context_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # Agent loop with tool calling
        answer = "I've gathered the relevant information. Based on your query, let me provide you with what I found."
        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info("agent_loop_iteration", iteration=iteration + 1)

            response = await self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1000,
            )

            total_tokens += response.usage.total_tokens if response.usage else 0
            choice = response.choices[0]

            # If no tool calls, we have the final answer
            if not choice.message.tool_calls:
                answer = choice.message.content or ""
                break

            # Execute tool calls
            messages.append({"role": "assistant", "content": choice.message.content, "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]})

            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                handler = TOOL_HANDLERS.get(func_name)
                if handler:
                    result = await handler(**func_args)
                else:
                    result = {"error": f"Unknown tool: {func_name}"}

                tool_calls_made.append(ToolCall(
                    tool_name=func_name,
                    arguments=func_args,
                    result=result,
                ))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            "resolution_complete",
            customer_id=query.customer_id,
            latency_ms=round(latency_ms, 2),
            tokens_used=total_tokens,
            tool_calls=len(tool_calls_made),
        )

        return ResolutionResult(
            answer=answer,
            sources=sources,
            confidence=0.85 if retrieved_docs else 0.7,
            tool_calls_made=tool_calls_made,
            tokens_used=total_tokens,
        )
