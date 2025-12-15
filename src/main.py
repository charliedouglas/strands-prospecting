"""Main entry point for the prospecting agent."""

import asyncio
import logging
from dotenv import load_dotenv

from src.config import Settings
from src.session import ProspectingSession, CLIFormatter
from src.cli import CLIApprovalHandler
from src.models import WorkflowRejectedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_welcome() -> None:
    """Print welcome message and system info."""
    print(CLIFormatter.header("PROSPECTING AGENT", width=70))
    print(f"Region: {CLIFormatter.dim('eu-west-2')}")
    print(f"Extended Thinking: {CLIFormatter.success('Enabled')}")
    print(f"Mock APIs: {CLIFormatter.success('Enabled')}\n")
    print("Commands:")
    print("  • Type your query and press Enter to start prospecting")
    print("  • Type 'session' to see session summary")
    print("  • Type 'history' to see query history")
    print("  • Type 'quit' or 'exit' to leave\n")


async def handle_query(session: ProspectingSession, query: str) -> bool:
    """
    Handle a single query through the prospecting workflow.

    Args:
        session: The prospecting session
        query: The user's query

    Returns:
        True if user wants to continue, False if they want to exit
    """
    try:
        print(CLIFormatter.progress("Analyzing query", 1, 5) + "\n")

        # Process the query
        result = await session.process_query(query)

        # Handle different response types
        if result.get("status") == "sufficient":
            print(CLIFormatter.format_result(result))
            return True

        elif result.get("status") == "insufficient":
            print(CLIFormatter.format_result(result))

            # Offer options
            print("\nWhat would you like to do?")
            print("  1. Refine your query and try again")
            print("  2. View the partial results we gathered")
            print("  3. Go back to main menu")

            choice = input("\nChoose (1-3): ").strip()
            if choice == "1":
                refined_query = input("Enter your refined query:\n> ").strip()
                if refined_query:
                    return await handle_query(session, refined_query)
            elif choice == "2":
                if result.get("summary"):
                    summary = result["summary"]
                    print(CLIFormatter.section("Partial Results"))
                    print(f"  Records found: {summary.get('total_records', 0)}")
                    print(f"  Companies: {summary.get('companies_found', 0)}")
                    print(f"  Individuals: {summary.get('individuals_found', 0)}")
            return True

        elif result.get("status") == "clarification_needed":
            print(CLIFormatter.format_result(result))

            # Get clarification response
            clarification = result.get("clarification", {})
            if clarification.get("options"):
                choice = input("\nYour choice: ").strip()

                # Try to map choice to option
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(clarification["options"]):
                        response = clarification["options"][idx]
                    else:
                        response = choice
                except ValueError:
                    response = choice

                # Retry with clarification
                refined_result = await session.clarify_and_retry(response)
                print(CLIFormatter.format_result(refined_result))

            else:
                response = input(f"\n{clarification.get('question', 'Your answer')}\n> ").strip()
                if response:
                    refined_result = await session.clarify_and_retry(response)
                    print(CLIFormatter.format_result(refined_result))

            return True

        else:
            print(CLIFormatter.warning(f"Unexpected status: {result.get('status')}"))
            return True

    except WorkflowRejectedError:
        print(CLIFormatter.error("Workflow cancelled by user."))
        return True

    except KeyboardInterrupt:
        print(f"\n{CLIFormatter.warning('Interrupted.')}")
        return True

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        print(CLIFormatter.error(f"Error: {str(e)[:100]}"))
        print("Please try again or type 'quit' to exit.")
        return True


def show_session_summary(session: ProspectingSession) -> None:
    """Display session summary."""
    summary = session.get_session_summary()
    print(CLIFormatter.header("SESSION SUMMARY"))
    print(f"Session ID: {CLIFormatter.dim(summary['session_id'])}")
    print(f"Total queries: {summary['total_queries']}")
    print(f"Successful: {CLIFormatter.success(str(summary['successful_queries']))}")
    if summary['failed_queries'] > 0:
        print(f"Failed: {CLIFormatter.error(str(summary['failed_queries']))}")
    if summary['clarifications_requested'] > 0:
        print(f"Clarifications: {summary['clarifications_requested']}")
    print(f"\nData collected:")
    print(f"  Records: {summary['total_records_found']}")
    print(f"  Companies: {summary['unique_companies']}")
    print(f"  Individuals: {summary['unique_individuals']}")
    print(f"  Total execution time: {summary['total_execution_time_ms']}ms\n")


def show_query_history(session: ProspectingSession) -> None:
    """Display query history."""
    history = session.get_query_history()
    if not history:
        print(CLIFormatter.warning("No queries in history yet."))
        return

    print(CLIFormatter.header("QUERY HISTORY"))
    for i, entry in enumerate(history, 1):
        status_indicator = "✓" if entry["status"] == "sufficient" else "⚠" if entry["status"] == "insufficient" else "○"
        print(f"{i}. [{status_indicator}] {entry['query'][:60]}")
        if entry.get("clarifications_count", 0) > 0:
            clarification_count = entry["clarifications_count"]
            print(f"   {CLIFormatter.dim(f'({clarification_count} clarifications)')}")
    print()


async def main() -> None:
    """Run the prospecting agent with an interactive session."""
    # Load environment variables
    load_dotenv()

    # Load configuration
    settings = Settings()

    # Apply settings to environment (AWS credentials, proxies, etc.)
    settings.apply_to_environment()

    # Print welcome
    print_welcome()

    # Create approval handler
    approval_handler = CLIApprovalHandler()

    # Create session
    session = ProspectingSession(settings, approval_handler)
    logger.info(f"Prospecting session {session.session_id} started")

    # Main interaction loop
    while True:
        try:
            print(CLIFormatter.CYAN + "💬 Enter your query (or 'quit', 'session', 'history'):" + CLIFormatter.RESET)
            user_input = input("> ").strip()

            # Check for special commands
            if user_input.lower() in ("quit", "exit", "q"):
                # Show final summary
                summary = session.get_session_summary()
                if summary["total_queries"] > 0:
                    print(f"\n{CLIFormatter.success('Session complete!')}")
                    print(f"Processed {summary['total_queries']} queries")
                    if summary["successful_queries"] > 0:
                        print(f"Successful: {summary['successful_queries']}")
                print("\n👋 Goodbye!\n")
                break

            elif user_input.lower() == "session":
                show_session_summary(session)
                continue

            elif user_input.lower() == "history":
                show_query_history(session)
                continue

            elif not user_input:
                print(CLIFormatter.warning("Please enter a query."))
                continue

            # Process the query
            should_continue = await handle_query(session, user_input)
            if not should_continue:
                break

        except KeyboardInterrupt:
            print(f"\n{CLIFormatter.warning('Interrupted.')}")
            continue

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            print(CLIFormatter.error(f"Unexpected error: {str(e)[:100]}"))
            print("Please try again or type 'quit' to exit.")
            continue


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{CLIFormatter.warning('Interrupted by user.')}")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n{CLIFormatter.error(f'Fatal error: {str(e)[:100]}')}")
