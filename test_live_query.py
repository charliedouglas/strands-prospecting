"""
Test script to run a live query through the approval workflow.
This simulates the full user interaction programmatically.
"""

import asyncio
import logging
from dotenv import load_dotenv

from src.config import Settings
from src.orchestrator import ProspectingOrchestrator
from src.models import PlanSummary, UserFeedback, ApprovalStatus, WorkflowRejectedError
from src.approval_handler import ApprovalHandler

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockApprovalHandler(ApprovalHandler):
    """
    Mock approval handler that simulates user responses.

    This allows us to test the workflow without requiring interactive input.
    """

    def __init__(self, responses: list[tuple[ApprovalStatus, str | None]]):
        """
        Initialize with pre-programmed responses.

        Args:
            responses: List of (status, feedback_text) tuples
                      e.g., [(ApprovalStatus.NEEDS_REVISION, "Add PitchBook")]
        """
        self.responses = responses
        self.current_response = 0

    async def request_approval(
        self,
        summary: PlanSummary,
        revision_number: int
    ) -> UserFeedback:
        """Request approval with pre-programmed response."""
        print("\n" + "=" * 70)
        print(f"EXECUTION PLAN REVIEW (Revision {revision_number})")
        print("=" * 70)
        print(f"\n📋 Query: {summary.query}")
        print(f"\n🔍 Data Sources ({summary.estimated_sources}):")
        for source in summary.data_sources:
            print(f"  • {source}")
        print(f"\n⚙️  Key Actions:")
        for i, action in enumerate(summary.key_actions, 1):
            print(f"  {i}. {action}")
        print(f"\n💭 Reasoning: {summary.reasoning_summary}")
        print(f"\n📊 Confidence: {summary.confidence:.0%}")
        print("=" * 70)

        # Get the pre-programmed response
        if self.current_response < len(self.responses):
            status, feedback_text = self.responses[self.current_response]
            self.current_response += 1

            if status == ApprovalStatus.APPROVED:
                print("\n✅ [Auto-approved for testing]")
            elif status == ApprovalStatus.NEEDS_REVISION:
                print(f"\n🔄 [Auto-requesting revision: {feedback_text}]")
            elif status == ApprovalStatus.REJECTED:
                print("\n❌ [Auto-rejected for testing]")

            from datetime import datetime
            return UserFeedback(
                status=status,
                feedback_text=feedback_text,
                timestamp=datetime.now()
            )
        else:
            # Default to approval if we run out of pre-programmed responses
            print("\n✅ [Auto-approved - no more test responses]")
            from datetime import datetime
            return UserFeedback(
                status=ApprovalStatus.APPROVED,
                timestamp=datetime.now()
            )


async def test_simple_approval():
    """Test with immediate approval."""
    print("\n" + "🧪 TEST 1: Simple Approval" + "\n" + "=" * 70)

    load_dotenv()
    settings = Settings()

    # Auto-approve on first presentation
    approval_handler = MockApprovalHandler([
        (ApprovalStatus.APPROVED, None)
    ])

    orchestrator = ProspectingOrchestrator(
        settings=settings,
        approval_handler=approval_handler
    )

    query = "Find UK tech companies that raised Series B funding in the last 12 months"

    try:
        result = await orchestrator.run(query)
        print(f"\n✅ TEST 1 PASSED")
        print(f"   Status: {result['status']}")
        print(f"   Steps in plan: {len(result['plan']['steps'])}")
        print(f"   Revisions: {len(result['workflow_state']['revisions'])}")
        return True
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_revision_then_approval():
    """Test with one revision request, then approval."""
    print("\n\n" + "🧪 TEST 2: Revision then Approval" + "\n" + "=" * 70)

    load_dotenv()
    settings = Settings()

    # Request revision, then approve
    approval_handler = MockApprovalHandler([
        (ApprovalStatus.NEEDS_REVISION, "Can you also include PitchBook for cross-referencing funding data?"),
        (ApprovalStatus.APPROVED, None)
    ])

    orchestrator = ProspectingOrchestrator(
        settings=settings,
        approval_handler=approval_handler
    )

    query = "Find UHNW individuals in London with tech sector wealth over £50m"

    try:
        result = await orchestrator.run(query)
        print(f"\n✅ TEST 2 PASSED")
        print(f"   Status: {result['status']}")
        print(f"   Steps in plan: {len(result['plan']['steps'])}")
        print(f"   Revisions: {len(result['workflow_state']['revisions'])}")

        # Verify we had 2 revisions (initial + revision)
        assert len(result['workflow_state']['revisions']) == 2, "Should have 2 revisions"
        print(f"   ✓ Correct number of revisions")
        return True
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rejection():
    """Test rejecting a plan."""
    print("\n\n" + "🧪 TEST 3: Rejection" + "\n" + "=" * 70)

    load_dotenv()
    settings = Settings()

    # Reject immediately
    approval_handler = MockApprovalHandler([
        (ApprovalStatus.REJECTED, None)
    ])

    orchestrator = ProspectingOrchestrator(
        settings=settings,
        approval_handler=approval_handler
    )

    query = "Find companies in the aerospace industry"

    try:
        result = await orchestrator.run(query)
        print(f"\n❌ TEST 3 FAILED: Should have raised WorkflowRejectedError")
        return False
    except WorkflowRejectedError:
        print(f"\n✅ TEST 3 PASSED: Rejection handled correctly")
        return True
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PROSPECTING AGENT - LIVE QUERY TESTS")
    print("=" * 70)
    print("\nThese tests will:")
    print("  1. Create real execution plans using the planner")
    print("  2. Generate summaries using the summarizer")
    print("  3. Simulate user approval/revision/rejection")
    print("  4. Verify the orchestration workflow")

    results = []

    # Run tests
    results.append(await test_simple_approval())
    results.append(await test_revision_then_approval())
    results.append(await test_rejection())

    # Summary
    print("\n\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")

    if all(results):
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED")

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
