"""Tests for approval workflow models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models import (
    ApprovalStatus,
    UserFeedback,
    PlanSummary,
    PlanRevision,
    ApprovalWorkflowState,
    ExecutionPlan,
    PlanStep,
    DataSource,
    WorkflowRejectedError,
)


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_approval_status_values(self):
        """Test that approval status enum has expected values."""
        assert ApprovalStatus.PENDING == "pending"
        assert ApprovalStatus.APPROVED == "approved"
        assert ApprovalStatus.REJECTED == "rejected"
        assert ApprovalStatus.NEEDS_REVISION == "needs_revision"


class TestUserFeedback:
    """Tests for UserFeedback model."""

    def test_user_feedback_approved(self):
        """Test creating approved feedback."""
        feedback = UserFeedback(
            status=ApprovalStatus.APPROVED,
            timestamp=datetime.now()
        )
        assert feedback.status == ApprovalStatus.APPROVED
        assert feedback.feedback_text is None
        assert isinstance(feedback.timestamp, datetime)

    def test_user_feedback_needs_revision(self):
        """Test creating feedback with modification request."""
        feedback = UserFeedback(
            status=ApprovalStatus.NEEDS_REVISION,
            feedback_text="Please add PitchBook to the data sources",
            timestamp=datetime.now()
        )
        assert feedback.status == ApprovalStatus.NEEDS_REVISION
        assert feedback.feedback_text == "Please add PitchBook to the data sources"

    def test_user_feedback_rejected(self):
        """Test creating rejected feedback."""
        feedback = UserFeedback(
            status=ApprovalStatus.REJECTED,
            timestamp=datetime.now()
        )
        assert feedback.status == ApprovalStatus.REJECTED
        assert feedback.feedback_text is None


class TestPlanSummary:
    """Tests for PlanSummary model."""

    def test_plan_summary_creation(self):
        """Test creating a plan summary."""
        summary = PlanSummary(
            query="Find UK tech companies with Series B funding",
            data_sources=["Crunchbase", "Companies House", "Internal CRM"],
            key_actions=[
                "Search for Series B funding rounds",
                "Get company details from Companies House",
                "Check for existing client relationships"
            ],
            estimated_sources=3,
            confidence=0.85,
            reasoning_summary="Will use Crunchbase for funding data, Companies House for corporate info, and CRM to filter existing clients."
        )

        assert summary.query == "Find UK tech companies with Series B funding"
        assert len(summary.data_sources) == 3
        assert "Crunchbase" in summary.data_sources
        assert len(summary.key_actions) == 3
        assert summary.estimated_sources == 3
        assert summary.confidence == 0.85

    def test_plan_summary_confidence_validation(self):
        """Test that confidence must be between 0 and 1."""
        # Valid confidence
        summary = PlanSummary(
            query="Test",
            data_sources=[],
            key_actions=[],
            estimated_sources=0,
            confidence=0.5,
            reasoning_summary="Test"
        )
        assert summary.confidence == 0.5

        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            PlanSummary(
                query="Test",
                data_sources=[],
                key_actions=[],
                estimated_sources=0,
                confidence=1.5,  # Invalid
                reasoning_summary="Test"
            )

        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            PlanSummary(
                query="Test",
                data_sources=[],
                key_actions=[],
                estimated_sources=0,
                confidence=-0.1,  # Invalid
                reasoning_summary="Test"
            )


class TestPlanRevision:
    """Tests for PlanRevision model."""

    def test_plan_revision_creation(self):
        """Test creating a plan revision."""
        # Create a minimal execution plan
        plan = ExecutionPlan(
            reasoning="Test reasoning",
            steps=[
                PlanStep(
                    step_id=1,
                    source=DataSource.CRUNCHBASE,
                    action="search_funding",
                    params={"investment_type": "series_b"},
                    reason="Find Series B funding"
                )
            ],
            estimated_sources=1,
            confidence=0.8
        )

        # Create a summary
        summary = PlanSummary(
            query="Test query",
            data_sources=["Crunchbase"],
            key_actions=["Search for funding"],
            estimated_sources=1,
            confidence=0.8,
            reasoning_summary="Test summary"
        )

        # Create a revision
        revision = PlanRevision(
            revision_number=1,
            original_plan=plan,
            summary=summary,
            user_feedback=None,
            timestamp=datetime.now()
        )

        assert revision.revision_number == 1
        assert revision.original_plan == plan
        assert revision.summary == summary
        assert revision.user_feedback is None
        assert isinstance(revision.timestamp, datetime)


class TestApprovalWorkflowState:
    """Tests for ApprovalWorkflowState model."""

    def test_workflow_state_initialization(self):
        """Test creating an empty workflow state."""
        state = ApprovalWorkflowState(
            query="Find UK tech companies",
            revisions=[],
            current_status=ApprovalStatus.PENDING,
            final_approved_plan=None
        )

        assert state.query == "Find UK tech companies"
        assert len(state.revisions) == 0
        assert state.current_status == ApprovalStatus.PENDING
        assert state.final_approved_plan is None
        assert state.current_revision_number == 0
        assert not state.is_complete

    def test_workflow_state_with_revisions(self):
        """Test workflow state with multiple revisions."""
        # Create a minimal execution plan
        plan = ExecutionPlan(
            reasoning="Test",
            steps=[],
            estimated_sources=1,
            confidence=0.8
        )

        summary = PlanSummary(
            query="Test",
            data_sources=[],
            key_actions=[],
            estimated_sources=1,
            confidence=0.8,
            reasoning_summary="Test"
        )

        revision1 = PlanRevision(
            revision_number=1,
            original_plan=plan,
            summary=summary,
            user_feedback=UserFeedback(
                status=ApprovalStatus.NEEDS_REVISION,
                feedback_text="Add more sources",
                timestamp=datetime.now()
            ),
            timestamp=datetime.now()
        )

        revision2 = PlanRevision(
            revision_number=2,
            original_plan=plan,
            summary=summary,
            user_feedback=UserFeedback(
                status=ApprovalStatus.APPROVED,
                timestamp=datetime.now()
            ),
            timestamp=datetime.now()
        )

        state = ApprovalWorkflowState(
            query="Test query",
            revisions=[revision1, revision2],
            current_status=ApprovalStatus.APPROVED,
            final_approved_plan=plan
        )

        assert state.current_revision_number == 2
        assert state.is_complete
        assert state.final_approved_plan == plan

    def test_workflow_state_is_complete(self):
        """Test the is_complete property."""
        # Pending - not complete
        state = ApprovalWorkflowState(
            query="Test",
            revisions=[],
            current_status=ApprovalStatus.PENDING
        )
        assert not state.is_complete

        # Needs revision - not complete
        state.current_status = ApprovalStatus.NEEDS_REVISION
        assert not state.is_complete

        # Approved - complete
        state.current_status = ApprovalStatus.APPROVED
        assert state.is_complete

        # Rejected - complete
        state.current_status = ApprovalStatus.REJECTED
        assert state.is_complete


class TestWorkflowRejectedError:
    """Tests for WorkflowRejectedError exception."""

    def test_workflow_rejected_error(self):
        """Test raising and catching WorkflowRejectedError."""
        with pytest.raises(WorkflowRejectedError) as exc_info:
            raise WorkflowRejectedError("User rejected the plan")

        assert str(exc_info.value) == "User rejected the plan"
        assert isinstance(exc_info.value, Exception)
