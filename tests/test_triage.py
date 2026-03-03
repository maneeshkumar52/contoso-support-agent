"""Tests for the triage agent."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from shared.models import CustomerQuery, Tier
from triage_agent.agent import TriageAgent
from triage_agent.router import determine_route


@pytest.fixture
def sample_query():
    return CustomerQuery(customer_id="CUST001", message="I forgot my password")


@pytest.fixture
def tier1_triage_response():
    return '{"tier": 1, "category": "password_reset", "confidence": 0.95, "reasoning": "Simple password reset", "auto_resolve_action": "initiate_password_reset"}'


@pytest.fixture
def tier2_triage_response():
    return '{"tier": 2, "category": "product_inquiry", "confidence": 0.88, "reasoning": "Policy question needs RAG", "auto_resolve_action": null}'


@pytest.fixture
def tier3_triage_response():
    return '{"tier": 3, "category": "fraud_report", "confidence": 0.99, "reasoning": "Fraud report needs human", "auto_resolve_action": null}'


@pytest.mark.asyncio
async def test_tier1_classification(sample_query, tier1_triage_response):
    """Test that password reset queries are classified as Tier 1."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = tier1_triage_response
    mock_response.usage.total_tokens = 150

    with patch.object(TriageAgent, '__init__', lambda self: None):
        agent = TriageAgent.__new__(TriageAgent)
        agent.settings = MagicMock()
        agent.settings.azure_openai_deployment = "gpt-4o"
        agent.client = AsyncMock()
        agent.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await agent.classify(sample_query)
        assert result.tier == Tier.TIER_1
        assert result.category == "password_reset"
        assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_tier2_classification(tier2_triage_response):
    """Test that policy questions are classified as Tier 2."""
    query = CustomerQuery(customer_id="CUST002", message="What are the fees for international transfers?")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = tier2_triage_response

    with patch.object(TriageAgent, '__init__', lambda self: None):
        agent = TriageAgent.__new__(TriageAgent)
        agent.settings = MagicMock()
        agent.settings.azure_openai_deployment = "gpt-4o"
        agent.client = AsyncMock()
        agent.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await agent.classify(query)
        assert result.tier == Tier.TIER_2


@pytest.mark.asyncio
async def test_tier3_classification(tier3_triage_response):
    """Test that fraud reports are classified as Tier 3."""
    query = CustomerQuery(customer_id="CUST003", message="Someone stole money from my account")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = tier3_triage_response

    with patch.object(TriageAgent, '__init__', lambda self: None):
        agent = TriageAgent.__new__(TriageAgent)
        agent.settings = MagicMock()
        agent.settings.azure_openai_deployment = "gpt-4o"
        agent.client = AsyncMock()
        agent.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await agent.classify(query)
        assert result.tier == Tier.TIER_3


def test_route_tier1():
    """Test routing logic for Tier 1."""
    from shared.models import TriageResult
    triage = TriageResult(tier=Tier.TIER_1, category="password_reset", confidence=0.95, reasoning="Simple", auto_resolve_action="initiate_password_reset")
    query = CustomerQuery(customer_id="CUST001", message="Reset my password")
    route = determine_route(triage, query)
    assert route["agent"] == "resolution"
    assert route["mode"] == "auto_resolve"


def test_route_escalates_low_confidence():
    """Test that low confidence Tier 1 escalates to Tier 2."""
    from shared.models import TriageResult
    triage = TriageResult(tier=Tier.TIER_1, category="unknown", confidence=0.5, reasoning="Uncertain")
    query = CustomerQuery(customer_id="CUST001", message="Something weird")
    route = determine_route(triage, query)
    assert route["effective_tier"] == Tier.TIER_2
