"""
CLI-based approval handler for the prospecting system.

This module provides a terminal-based interface for users to review
and approve execution plans.
"""

from datetime import datetime

from src.models import PlanSummary, UserFeedback, ApprovalStatus
from src.approval_handler import ApprovalHandler


class CLIApprovalHandler(ApprovalHandler):
    """
    Command-line interface approval handler.

    This handler presents plan summaries to users in the terminal
    and collects their approval decisions through standard input.
    """

    async def request_approval(
        self,
        summary: PlanSummary,
        revision_number: int
    ) -> UserFeedback:
        """
        Request approval from the user via CLI.

        Displays the plan summary in a readable format and prompts
        the user for their decision (approve, modify, or reject).

        Args:
            summary: Human-friendly summary of the execution plan
            revision_number: Which revision this is (1, 2, 3, etc.)

        Returns:
            UserFeedback with the user's decision and any feedback text
        """
        # Display the plan summary
        self._display_summary(summary, revision_number)

        # Collect user decision
        return await self._collect_user_decision()

    def _display_summary(self, summary: PlanSummary, revision_number: int) -> None:
        """
        Display the plan summary in a user-friendly format.

        Args:
            summary: Plan summary to display
            revision_number: Revision number to show in header
        """
        # Header
        print(f"\n{'=' * 70}")
        print(f"EXECUTION PLAN REVIEW (Revision {revision_number})")
        print(f"{'=' * 70}")

        # Query
        print(f"\n📋 Query:")
        print(f"  {summary.query}")

        # Data sources
        print(f"\n🔍 Data Sources ({summary.estimated_sources} total):")
        for source in summary.data_sources:
            print(f"  • {source}")

        # Key actions
        print(f"\n⚙️  What will happen:")
        for i, action in enumerate(summary.key_actions, 1):
            print(f"  {i}. {action}")

        # Planner's reasoning
        print(f"\n💭 Planner's Reasoning:")
        # Wrap reasoning text at 66 characters for readability
        reasoning = summary.reasoning_summary
        words = reasoning.split()
        lines = []
        current_line = "  "

        for word in words:
            if len(current_line) + len(word) + 1 <= 68:  # 68 = 70 - 2 for indent
                current_line += word + " "
            else:
                lines.append(current_line.rstrip())
                current_line = "  " + word + " "

        if current_line.strip():
            lines.append(current_line.rstrip())

        print("\n".join(lines))

        # Confidence
        confidence_percent = int(summary.confidence * 100)
        confidence_bar = "█" * (confidence_percent // 5) + "░" * (20 - confidence_percent // 5)
        print(f"\n📊 Confidence: {confidence_bar} {confidence_percent}%")

        print(f"\n{'=' * 70}")

    async def _collect_user_decision(self) -> UserFeedback:
        """
        Collect the user's approval decision.

        Prompts the user for their choice and collects any feedback text
        if they request modifications.

        Returns:
            UserFeedback with status and optional feedback text
        """
        # Display options
        print("\n✨ What would you like to do?")
        print("  [A] Approve - Proceed with this plan")
        print("  [M] Modify - Provide feedback to revise the plan")
        print("  [R] Reject - Cancel this query")

        # Loop until we get a valid choice
        while True:
            try:
                choice = input("\nYour choice (A/M/R): ").strip().upper()

                if choice == 'A':
                    print("\n✅ Plan approved! Proceeding with execution...")
                    return UserFeedback(
                        status=ApprovalStatus.APPROVED,
                        feedback_text=None,
                        timestamp=datetime.now()
                    )

                elif choice == 'M':
                    print("\n📝 Please describe what you'd like to change:")
                    feedback_text = input("> ").strip()

                    if not feedback_text:
                        print("⚠️  Feedback cannot be empty. Please describe what you'd like to change.")
                        continue

                    print(f"\n🔄 Revising plan based on your feedback...")
                    return UserFeedback(
                        status=ApprovalStatus.NEEDS_REVISION,
                        feedback_text=feedback_text,
                        timestamp=datetime.now()
                    )

                elif choice == 'R':
                    # Confirm rejection
                    confirm = input("\n⚠️  Are you sure you want to reject this plan? (y/N): ").strip().lower()

                    if confirm == 'y' or confirm == 'yes':
                        print("\n❌ Plan rejected. Workflow cancelled.")
                        return UserFeedback(
                            status=ApprovalStatus.REJECTED,
                            feedback_text=None,
                            timestamp=datetime.now()
                        )
                    else:
                        print("\n↩️  Rejection cancelled. Please choose again.")
                        continue

                else:
                    print("⚠️  Invalid choice. Please enter A, M, or R.")
                    continue

            except (EOFError, KeyboardInterrupt):
                # Handle Ctrl+C or EOF gracefully
                print("\n\n⚠️  Input interrupted. Treating as rejection.")
                return UserFeedback(
                    status=ApprovalStatus.REJECTED,
                    feedback_text="User interrupted input",
                    timestamp=datetime.now()
                )
            except Exception as e:
                print(f"\n⚠️  Error collecting input: {e}")
                print("Please try again.")
                continue
