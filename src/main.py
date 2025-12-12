"""Main entry point for the prospecting agent."""

import asyncio
import logging
from dotenv import load_dotenv

from src.config import Settings
from src.orchestrator import ProspectingOrchestrator
from src.cli import CLIApprovalHandler
from src.models import WorkflowRejectedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the prospecting agent with user approval workflow."""
    # Load environment variables
    load_dotenv()

    # Load configuration
    settings = Settings()

    # Print header
    print("\n" + "=" * 70)
    print("PROSPECTING AGENT WITH USER APPROVAL")
    print("=" * 70)
    print(f"\n🌍 Region: {settings.aws_region}")
    print(f"🤖 Planner Model: {settings.planner_model}")
    print(f"⚡ Extended Thinking: {'Enabled' if settings.enable_extended_thinking else 'Disabled'}")
    print(f"🔧 Mock APIs: {'Enabled' if settings.mock_apis else 'Disabled'}")
    print(f"\n{'=' * 70}\n")

    # Create CLI approval handler
    approval_handler = CLIApprovalHandler()

    # Create orchestrator
    orchestrator = ProspectingOrchestrator(
        settings=settings,
        approval_handler=approval_handler
    )

    logger.info("Prospecting orchestrator initialized and ready")

    # Main interaction loop
    while True:
        try:
            # Get user query
            print("\n💬 Enter your prospecting query (or 'quit' to exit):")
            query = input("> ").strip()

            # Check for exit
            if query.lower() in ('quit', 'exit', 'q'):
                print("\n👋 Goodbye!")
                break

            # Skip empty queries
            if not query:
                print("⚠️  Please enter a query.")
                continue

            # Run workflow
            print("\n🔄 Processing your query...\n")
            result = await orchestrator.run(query)

            # Display result
            print(f"\n{'=' * 70}")
            print("WORKFLOW COMPLETE")
            print(f"{'=' * 70}")
            print(f"\n✅ Status: {result['status'].title()}")

            if result['status'] == 'executed':
                summary = result['summary']
                print(f"\n📊 EXECUTION SUMMARY:")
                print(f"   Steps Executed: {summary['steps_executed']}")
                print(f"   ✓ Succeeded: {summary['steps_succeeded']}")
                if summary['steps_failed'] > 0:
                    print(f"   ✗ Failed: {summary['steps_failed']}")
                print(f"   📝 Total Records: {summary['total_records']}")
                print(f"   ⏱️  Execution Time: {summary['execution_time_ms']}ms")
                print(f"   🔍 Sources: {', '.join(summary['sources_queried'])}")

                # Show individual step results
                print(f"\n📋 STEP RESULTS:")
                for i, step_result in enumerate(result['execution_results']['results'], 1):
                    status = "✓" if step_result['success'] else "✗"
                    source = step_result['source']
                    records = step_result['record_count']
                    time = step_result['execution_time_ms']
                    print(f"   {status} Step {i}: {source} ({records} records, {time}ms)")
                    if step_result.get('error'):
                        print(f"      Error: {step_result['error']}")

            elif result['status'] == 'approved':
                print(f"📋 Plan: {len(result['plan']['steps'])} steps ready for execution")
                print(f"🔄 Revisions: {len(result['workflow_state']['revisions'])}")
                print(f"\n💡 {result['message']}")
            elif result['status'] == 'clarification_needed':
                print(f"❓ Clarification needed: {result['clarification']['question']}")
                if result['clarification'].get('options'):
                    print(f"   Options: {', '.join(result['clarification']['options'])}")

        except WorkflowRejectedError:
            print("\n❌ Workflow cancelled by user.")
            continue

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'quit' to exit or press Enter to continue.")
            continue

        except Exception as e:
            logger.error(f"Error in workflow: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")
            continue


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
