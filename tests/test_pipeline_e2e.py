"""End-to-end pipeline tests with mocked Azure services."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from shared.models import CustomerQuery, Tier


@pytest.mark.asyncio
async def test_tier1_pipeline_flow():
    """Test that Tier 1 queries flow through auto-resolution."""
    query = CustomerQuery(customer_id="CUST001", message="I need to reset my password")

    triage_json = '{"tier": 1, "category": "password_reset", "confidence": 0.96, "reasoning": "Password reset", "auto_resolve_action": "initiate_password_reset"}'
    resolution_content = "Your password reset has been initiated. Check your email for the reset link."

    mock_triage_response = MagicMock()
    mock_triage_response.choices[0].message.content = triage_json
    mock_triage_response.usage.total_tokens = 100

    mock_resolution_response = MagicMock()
    mock_resolution_response.choices[0].message.content = resolution_content
    mock_resolution_response.choices[0].message.tool_calls = None
    mock_resolution_response.usage.total_tokens = 150

    mock_search_client = MagicMock()

    with patch("shared.azure_clients.AzureClients.get_openai_client") as mock_oai, \
         patch("shared.azure_clients.AzureClients.get_search_client", return_value=mock_search_client), \
         patch("shared.azure_clients.AzureClients.get_cosmos_client") as mock_cosmos:

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[mock_triage_response, mock_resolution_response]
        )
        mock_oai.return_value = mock_client

        mock_cosmos_client = AsyncMock()
        mock_cosmos_client.__aenter__ = AsyncMock(return_value=mock_cosmos_client)
        mock_cosmos_client.__aexit__ = AsyncMock(return_value=False)
        mock_cosmos_client.get_database_client.return_value.get_container_client.return_value.create_item = AsyncMock()
        mock_cosmos.return_value = mock_cosmos_client

        from orchestrator.pipeline import SupportPipeline
        pipeline = SupportPipeline()
        result = await pipeline.run(query)

        assert result is not None
        assert result.session_id == query.session_id
        assert "triage_agent" in result.agents_used


@pytest.mark.asyncio
async def test_pipeline_error_handling():
    """Test that pipeline handles errors gracefully."""
    query = CustomerQuery(customer_id="CUST001", message="Test error handling")

    mock_search_client = MagicMock()

    with patch("shared.azure_clients.AzureClients.get_openai_client") as mock_oai, \
         patch("shared.azure_clients.AzureClients.get_search_client", return_value=mock_search_client):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Azure service unavailable"))
        mock_oai.return_value = mock_client

        from orchestrator.pipeline import SupportPipeline
        pipeline = SupportPipeline()
        result = await pipeline.run(query)

        assert result is not None
        assert result.final_response is not None
        # When Azure fails, triage defaults to Tier 2 with 0.5 confidence, which escalates to Tier 3
        # (escalation handler) and returns a human-escalation or apology message
        assert len(result.final_response) > 0
