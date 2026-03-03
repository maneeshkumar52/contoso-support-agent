"""Tool definitions for the resolution agent using OpenAI function calling."""
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List
import structlog

logger = structlog.get_logger(__name__)

# Mock customer data
MOCK_ACCOUNTS = {
    "CUST001": {"balance": 4523.67, "account_type": "Current Account", "currency": "GBP", "card_status": "active"},
    "CUST002": {"balance": 12890.45, "account_type": "Savings Account", "currency": "GBP", "card_status": "blocked"},
    "CUST003": {"balance": 234.12, "account_type": "Current Account", "currency": "GBP", "card_status": "active"},
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_account_balance",
            "description": "Check the current account balance for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "The customer's unique ID"}
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_transactions",
            "description": "Get recent transactions for a customer account",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "The customer's unique ID"},
                    "days": {"type": "integer", "description": "Number of days of history to retrieve", "default": 30},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_password_reset",
            "description": "Initiate a password reset for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "The customer's unique ID"}
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_card_status",
            "description": "Check the status of a customer's debit or credit card",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "The customer's unique ID"}
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_policy_details",
            "description": "Retrieve details about a specific banking policy",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "The policy identifier (e.g., 'overdraft', 'international_transfers')"}
                },
                "required": ["policy_id"],
            },
        },
    },
]


async def check_account_balance(customer_id: str) -> Dict[str, Any]:
    """Return mock account balance for a customer."""
    account = MOCK_ACCOUNTS.get(customer_id, {"balance": 1000.00, "account_type": "Current Account", "currency": "GBP"})
    result = {
        "customer_id": customer_id,
        "balance": account["balance"],
        "currency": account["currency"],
        "account_type": account["account_type"],
        "last_updated": datetime.utcnow().isoformat(),
    }
    logger.info("tool_check_account_balance", customer_id=customer_id, balance=result["balance"])
    return result


async def get_recent_transactions(customer_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """Return mock recent transactions."""
    merchants = ["Tesco", "Amazon", "Netflix", "Costa Coffee", "Shell Petrol", "John Lewis", "ASOS"]
    categories = ["groceries", "shopping", "entertainment", "food_drink", "transport", "utilities"]

    transactions = []
    for i in range(min(days, 10)):
        date = (datetime.utcnow() - timedelta(days=i * 3)).strftime("%Y-%m-%d")
        transactions.append({
            "date": date,
            "description": f"{random.choice(merchants)} Purchase",
            "amount": -round(random.uniform(5.00, 150.00), 2),
            "category": random.choice(categories),
            "merchant": random.choice(merchants),
            "reference": f"TXN{random.randint(100000, 999999)}",
        })

    logger.info("tool_get_recent_transactions", customer_id=customer_id, count=len(transactions))
    return transactions


async def initiate_password_reset(customer_id: str) -> Dict[str, Any]:
    """Initiate password reset for customer."""
    result = {
        "success": True,
        "customer_id": customer_id,
        "message": "Password reset email sent to registered email address",
        "reset_link_expires_in": "24 hours",
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info("tool_initiate_password_reset", customer_id=customer_id)
    return result


async def check_card_status(customer_id: str) -> Dict[str, Any]:
    """Check card status for customer."""
    account = MOCK_ACCOUNTS.get(customer_id, {"card_status": "active"})
    result = {
        "customer_id": customer_id,
        "card_number_masked": "****-****-****-4523",
        "status": account.get("card_status", "active"),
        "expiry": "12/27",
        "daily_limit": 500.00,
        "contactless_limit": 100.00,
    }
    logger.info("tool_check_card_status", customer_id=customer_id, status=result["status"])
    return result


async def get_policy_details(policy_id: str) -> Dict[str, Any]:
    """Return mock policy details."""
    policies = {
        "overdraft": {
            "policy_id": "overdraft",
            "title": "Arranged Overdraft Policy",
            "interest_rate": "39.9% EAR",
            "fee": "No daily fee for arranged overdraft",
            "limit": "Up to £5,000 subject to credit check",
            "how_to_apply": "Apply online via the app or call 0800-CONTOSO",
        },
        "international_transfers": {
            "policy_id": "international_transfers",
            "title": "International Transfer Policy",
            "fee": "£5 per transfer + 0.5% of amount",
            "processing_time": "1-3 business days for SWIFT transfers",
            "limits": "Maximum £25,000 per transaction",
            "currencies": "140+ currencies supported",
        },
        "savings_rates": {
            "policy_id": "savings_rates",
            "title": "Savings Account Interest Rates",
            "instant_access": "3.5% AER",
            "fixed_1yr": "4.2% AER",
            "fixed_2yr": "4.5% AER",
            "isa_rate": "3.8% AER (tax-free)",
        },
    }
    result = policies.get(policy_id, {"policy_id": policy_id, "error": "Policy not found in database"})
    logger.info("tool_get_policy_details", policy_id=policy_id)
    return result


TOOL_HANDLERS = {
    "check_account_balance": check_account_balance,
    "get_recent_transactions": get_recent_transactions,
    "initiate_password_reset": initiate_password_reset,
    "check_card_status": check_card_status,
    "get_policy_details": get_policy_details,
}
