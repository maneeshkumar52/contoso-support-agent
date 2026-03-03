import asyncio
import sys
sys.path.insert(0, '.')

async def main():
    print("=== Contoso Support Agent - End-to-End Demo ===\n")

    # Test 1: Chunker (no Azure needed)
    from knowledge_base.chunker import RecursiveTextChunker
    chunker = RecursiveTextChunker(chunk_size=500, chunk_overlap=100)
    sample_doc = """# Banking Policy
## Password Reset Policy
Customers can reset their password via the mobile app or online banking portal.
The process requires verification of identity through SMS OTP or email confirmation.
Passwords must be at least 8 characters and contain uppercase, lowercase, and numbers.

## Balance Inquiry
Customers can check their balance via:
1. Mobile banking app
2. Online banking portal
3. ATM
4. Phone banking (0800-123-456)

## Card Activation
New cards must be activated within 30 days of receipt via:
- Mobile app PIN setup
- ATM PIN setup
- Calling 0800-123-456
"""
    chunks = chunker.split_text(sample_doc, metadata={"source": "banking_policy.md"})
    print(f"Chunker: split document into {len(chunks)} chunks")
    for i, c in enumerate(chunks[:2]):
        print(f"  Chunk {i+1}: {c['content'][:80]}...")

    # Test 2: Triage tools (mock data - no Azure needed)
    from resolution_agent.tools import check_account_balance, get_recent_transactions, check_card_status
    balance = await check_account_balance("CUST001")
    print(f"\nAccount balance tool: GBP {balance.get('balance', 'N/A')} ({balance.get('account_type', '')})")

    txns = await get_recent_transactions("CUST001", days=7)
    print(f"Transactions tool: returned {len(txns)} transactions")
    if txns:
        print(f"  Latest: {txns[0]}")

    card = await check_card_status("CUST001")
    print(f"Card status tool: {card.get('status', 'N/A')}")

    # Test 3: Shared models
    from shared.models import CustomerQuery, TriageResult, Tier
    query = CustomerQuery(
        customer_id="CUST001",
        message="I need to reset my password",
        session_id="sess-001",
        channel="chat"
    )
    print(f"\nModels: CustomerQuery created - '{query.message}'")

    triage_result = TriageResult(
        tier=Tier.TIER_1,
        category="password_reset",
        confidence=0.95,
        reasoning="Simple password reset request - auto-resolvable"
    )
    print(f"Models: TriageResult - Tier {triage_result.tier.value}, confidence {triage_result.confidence}")

    print("\n=== All core components working without Azure credentials ===")
    print("To run with real Azure services, set environment variables in .env")

asyncio.run(main())
