"""Tests for the resolution agent tools."""
import pytest
import asyncio
from resolution_agent.tools import (
    check_account_balance, get_recent_transactions,
    initiate_password_reset, check_card_status, get_policy_details,
)


@pytest.mark.asyncio
async def test_check_account_balance_known_customer():
    result = await check_account_balance("CUST001")
    assert "balance" in result
    assert result["customer_id"] == "CUST001"
    assert result["balance"] == 4523.67


@pytest.mark.asyncio
async def test_check_account_balance_unknown_customer():
    result = await check_account_balance("CUST999")
    assert "balance" in result
    assert result["balance"] == 1000.00


@pytest.mark.asyncio
async def test_get_recent_transactions():
    result = await get_recent_transactions("CUST001", days=30)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "date" in result[0]
    assert "amount" in result[0]


@pytest.mark.asyncio
async def test_initiate_password_reset():
    result = await initiate_password_reset("CUST001")
    assert result["success"] is True
    assert "customer_id" in result


@pytest.mark.asyncio
async def test_check_card_status_blocked():
    result = await check_card_status("CUST002")
    assert result["status"] == "blocked"


@pytest.mark.asyncio
async def test_get_policy_details():
    result = await get_policy_details("overdraft")
    assert "policy_id" in result
    assert result["policy_id"] == "overdraft"
    assert "interest_rate" in result


@pytest.mark.asyncio
async def test_get_policy_details_unknown():
    result = await get_policy_details("unknown_policy")
    assert "error" in result
