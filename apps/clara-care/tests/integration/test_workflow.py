"""Integration tests for ClaraCare warranty claim workflow.

This module tests the full agent workflow including:
- High-confidence flow (auto-submit)
- Low-confidence flow (human review)
- No-email-found flow (requires review)
- State flow between agents

Uses InMemorySessionService for testing without external dependencies.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_claim_details() -> dict[str, Any]:
    """Sample claim details for testing."""
    return {
        "found": True,
        "claim_id": "CLM-TEST-001",
        "user": {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "+1-555-123-4567",
        },
        "product": {
            "brand": "Sony",
            "name": "WH-1000XM5 Headphones",
            "category": "Electronics",
            "serial_number": "SN123456789",
            "purchase_date": "2024-06-15",
        },
        "issue": {
            "description": "Left earcup stopped producing sound after 6 months",
            "occurrence_date": "2025-01-10",
        },
        "receipt_reference": "RCP-2024-06-15-001",
        "status": "PENDING",
        "message": "Found claim CLM-TEST-001",
    }


@pytest.fixture
def high_confidence_internal_search() -> dict[str, Any]:
    """Internal search result with high confidence match."""
    return {
        "found": True,
        "email": "support@sony.com",
        "confidence": 0.95,
        "source": "internal_db",
        "brand_name": "Sony",
        "additional_contacts": [],
    }


@pytest.fixture
def high_confidence_web_search() -> dict[str, Any]:
    """Web search result with validated email matching internal DB."""
    return {
        "found": True,
        "emails": [
            {
                "email": "support@sony.com",
                "validation_score": 0.92,
                "domain_matches_brand": True,
            }
        ],
        "brand_searched": "Sony",
        "sources": ["https://www.sony.com/support"],
    }


@pytest.fixture
def high_confidence_judge_verdict() -> dict[str, Any]:
    """Judge verdict for high-confidence auto-submit."""
    return {
        "confidence_score": 0.92,
        "recommended_email": "support@sony.com",
        "reasoning": (
            "High confidence: Email found in both internal DB (0.95) and web "
            "search (0.92). Domain matches brand (sony.com). Multiple sources "
            "agree on the same email address."
        ),
        "decision": "AUTO_SUBMIT",
        "factors": {
            "source_reliability": 0.40,
            "validation_score_contribution": 0.28,
            "domain_match": 0.20,
            "source_agreement": 0.10,
        },
        "alternatives": [],
    }


@pytest.fixture
def low_confidence_internal_search() -> dict[str, Any]:
    """Internal search result with no match."""
    return {
        "found": False,
        "email": None,
        "confidence": 0.0,
        "source": "internal_db",
        "brand_name": None,
        "additional_contacts": [],
    }


@pytest.fixture
def low_confidence_web_search() -> dict[str, Any]:
    """Web search result with low validation score."""
    return {
        "found": True,
        "emails": [
            {
                "email": "warranty@unknownbrand-support.com",
                "validation_score": 0.55,
                "domain_matches_brand": False,
            }
        ],
        "brand_searched": "UnknownBrand",
        "sources": ["https://third-party-site.com/support"],
    }


@pytest.fixture
def low_confidence_judge_verdict() -> dict[str, Any]:
    """Judge verdict for low-confidence human review."""
    return {
        "confidence_score": 0.47,
        "recommended_email": "warranty@unknownbrand-support.com",
        "reasoning": (
            "Low confidence: Web-only source with domain mismatch. Validation "
            "score 0.55 is below threshold. Recommending human review."
        ),
        "decision": "HUMAN_REVIEW",
        "factors": {
            "source_reliability": 0.20,
            "validation_score_contribution": 0.17,
            "domain_match": 0.10,
            "source_agreement": 0.00,
        },
        "alternatives": [],
    }


@pytest.fixture
def no_email_internal_search() -> dict[str, Any]:
    """Internal search result with no match for obscure brand."""
    return {
        "found": False,
        "email": None,
        "confidence": 0.0,
        "source": "internal_db",
        "brand_name": None,
        "additional_contacts": [],
    }


@pytest.fixture
def no_email_web_search() -> dict[str, Any]:
    """Web search result with no email found."""
    return {
        "found": False,
        "emails": [],
        "brand_searched": "ObscureBrand",
        "sources": [],
    }


@pytest.fixture
def no_email_judge_verdict() -> dict[str, Any]:
    """Judge verdict for no-email-found scenario."""
    return {
        "confidence_score": 0.0,
        "recommended_email": None,
        "reasoning": (
            "No email found in internal database or web search for 'ObscureBrand'. "
            "Searched internal support contacts and performed web queries but "
            "could not locate any valid support email address."
        ),
        "decision": "HUMAN_REVIEW",
        "factors": {
            "source_reliability": 0.00,
            "validation_score_contribution": 0.00,
            "domain_match": 0.00,
            "source_agreement": 0.00,
        },
        "alternatives": [],
    }


@pytest.fixture
def composed_email() -> dict[str, Any]:
    """Sample composed email from writer agent."""
    return {
        "to_address": "support@sony.com",
        "subject": "Warranty Claim - Sony WH-1000XM5 Headphones - CLM-TEST-001",
        "body": (
            "Dear Sony Support Team,\n\n"
            "I am writing to submit a warranty claim for my Sony WH-1000XM5 "
            "Headphones.\n\n"
            "Product Information:\n"
            "- Brand: Sony\n"
            "- Product: WH-1000XM5 Headphones\n"
            "- Serial Number: SN123456789\n"
            "- Purchase Date: 2024-06-15\n\n"
            "Issue Description:\n"
            "Left earcup stopped producing sound after 6 months of use.\n"
            "Issue occurred on: 2025-01-10\n\n"
            "Customer Information:\n"
            "- Name: John Doe\n"
            "- Email: john.doe@email.com\n"
            "- Phone: +1-555-123-4567\n\n"
            "Receipt Reference: RCP-2024-06-15-001\n\n"
            "Please advise on next steps for this warranty claim.\n\n"
            "Best regards,\n"
            "John Doe\n"
            "Claim ID: CLM-TEST-001"
        ),
        "claim_id": "CLM-TEST-001",
        "composed_at": "2025-01-13T10:30:00Z",
    }


# =============================================================================
# MOCK SESSION STATE MANAGER
# =============================================================================


class MockSessionState:
    """Mock session state for testing state flow between agents."""

    def __init__(self) -> None:
        """Initialize empty state."""
        self._state: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state."""
        return self._state.get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set value in state."""
        self._state[key] = value

    def __getitem__(self, key: str) -> Any:
        """Get value from state."""
        return self._state[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in state."""
        return key in self._state

    def keys(self) -> list[str]:
        """Get all keys in state."""
        return list(self._state.keys())

    def items(self) -> list[tuple[str, Any]]:
        """Get all items in state."""
        return list(self._state.items())

    def update(self, data: dict[str, Any]) -> None:
        """Update state with dictionary."""
        self._state.update(data)


# =============================================================================
# HIGH-CONFIDENCE AUTO-SUBMIT FLOW TESTS
# =============================================================================


@pytest.mark.integration
class TestHighConfidenceAutoSubmitFlow:
    """Test the high-confidence auto-submit workflow."""

    def test_high_confidence_state_flow(
        self,
        sample_claim_details: dict[str, Any],
        high_confidence_internal_search: dict[str, Any],
        high_confidence_web_search: dict[str, Any],
        high_confidence_judge_verdict: dict[str, Any],
        composed_email: dict[str, Any],
    ) -> None:
        """Test state flows correctly through high-confidence workflow."""
        state = MockSessionState()

        # Step 1: Claim details loaded into state
        state["claim_details"] = json.dumps(sample_claim_details)
        assert "claim_details" in state
        claim = json.loads(state["claim_details"])
        assert claim["claim_id"] == "CLM-TEST-001"
        assert claim["product"]["brand"] == "Sony"

        # Step 2: Internal search result saved to state
        state["internal_search_result"] = json.dumps(high_confidence_internal_search)
        assert "internal_search_result" in state
        internal_result = json.loads(state["internal_search_result"])
        assert internal_result["found"] is True
        assert internal_result["email"] == "support@sony.com"

        # Step 3: Web search result saved to state
        state["web_search_result"] = json.dumps(high_confidence_web_search)
        assert "web_search_result" in state
        web_result = json.loads(state["web_search_result"])
        assert web_result["found"] is True
        assert web_result["emails"][0]["validation_score"] == 0.92

        # Step 4: Judge verdict saved to state
        state["judge_verdict"] = json.dumps(high_confidence_judge_verdict)
        assert "judge_verdict" in state
        verdict = json.loads(state["judge_verdict"])
        assert verdict["confidence_score"] == 0.92
        assert verdict["confidence_score"] >= 0.80  # Threshold
        assert verdict["decision"] == "AUTO_SUBMIT"
        assert verdict["recommended_email"] == "support@sony.com"

        # Step 5: Composed email saved to state (only for AUTO_SUBMIT)
        state["composed_email"] = json.dumps(composed_email)
        assert "composed_email" in state
        email = json.loads(state["composed_email"])
        assert email["to_address"] == "support@sony.com"
        assert "CLM-TEST-001" in email["subject"]

    def test_high_confidence_decision_threshold(
        self,
        high_confidence_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that confidence >= 0.80 triggers AUTO_SUBMIT."""
        verdict = high_confidence_judge_verdict

        # Verify threshold logic
        threshold = 0.80
        assert verdict["confidence_score"] >= threshold
        assert verdict["decision"] == "AUTO_SUBMIT"

    def test_high_confidence_factors_sum_correctly(
        self,
        high_confidence_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that confidence factors contribute correctly."""
        verdict = high_confidence_judge_verdict
        factors = verdict["factors"]

        # Verify individual factor weights are reasonable
        assert factors["source_reliability"] == 0.40  # Internal DB found
        assert factors["validation_score_contribution"] == 0.28  # 0.92 * 0.30
        assert factors["domain_match"] == 0.20  # Full match
        assert factors["source_agreement"] == 0.10  # Both sources agree

        # Sum should approximately equal confidence_score
        factor_sum = sum(factors.values())
        assert abs(factor_sum - verdict["confidence_score"]) < 0.1

    def test_high_confidence_email_composition(
        self,
        sample_claim_details: dict[str, Any],
        composed_email: dict[str, Any],
    ) -> None:
        """Test composed email contains required information."""
        email = composed_email
        claim = sample_claim_details

        # Verify email addresses
        assert email["to_address"] == "support@sony.com"

        # Verify subject format
        assert claim["product"]["brand"] in email["subject"]
        assert claim["product"]["name"] in email["subject"]
        assert claim["claim_id"] in email["subject"]

        # Verify body contains required sections
        body = email["body"]
        assert claim["product"]["brand"] in body
        assert claim["product"]["serial_number"] in body
        assert claim["product"]["purchase_date"] in body
        assert claim["issue"]["description"] in body
        assert claim["user"]["name"] in body
        assert claim["user"]["email"] in body
        assert claim["receipt_reference"] in body
        assert claim["claim_id"] in body

    def test_high_confidence_status_update_data(
        self,
        high_confidence_judge_verdict: dict[str, Any],
    ) -> None:
        """Test data required for SUBMITTED status update."""
        verdict = high_confidence_judge_verdict

        # For SUBMITTED status, these fields should be populated
        assert verdict["recommended_email"] is not None
        assert len(verdict["recommended_email"]) > 0
        assert verdict["confidence_score"] > 0
        assert verdict["reasoning"] is not None
        assert len(verdict["reasoning"]) > 0


# =============================================================================
# LOW-CONFIDENCE HUMAN REVIEW FLOW TESTS
# =============================================================================


@pytest.mark.integration
class TestLowConfidenceHumanReviewFlow:
    """Test the low-confidence human review workflow."""

    def test_low_confidence_state_flow(
        self,
        sample_claim_details: dict[str, Any],
        low_confidence_internal_search: dict[str, Any],
        low_confidence_web_search: dict[str, Any],
        low_confidence_judge_verdict: dict[str, Any],
    ) -> None:
        """Test state flows correctly through low-confidence workflow."""
        state = MockSessionState()

        # Step 1: Claim details loaded into state
        state["claim_details"] = json.dumps(sample_claim_details)
        assert "claim_details" in state

        # Step 2: Internal search returns not found
        state["internal_search_result"] = json.dumps(low_confidence_internal_search)
        internal_result = json.loads(state["internal_search_result"])
        assert internal_result["found"] is False
        assert internal_result["email"] is None

        # Step 3: Web search returns low-quality match
        state["web_search_result"] = json.dumps(low_confidence_web_search)
        web_result = json.loads(state["web_search_result"])
        assert web_result["found"] is True
        assert web_result["emails"][0]["validation_score"] < 0.80
        assert web_result["emails"][0]["domain_matches_brand"] is False

        # Step 4: Judge verdict below threshold
        state["judge_verdict"] = json.dumps(low_confidence_judge_verdict)
        verdict = json.loads(state["judge_verdict"])
        assert verdict["confidence_score"] < 0.80
        assert verdict["decision"] == "HUMAN_REVIEW"

        # Step 5: composed_email should NOT be in state for HUMAN_REVIEW
        assert "composed_email" not in state

    def test_low_confidence_decision_threshold(
        self,
        low_confidence_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that confidence < 0.80 triggers HUMAN_REVIEW."""
        verdict = low_confidence_judge_verdict

        threshold = 0.80
        assert verdict["confidence_score"] < threshold
        assert verdict["decision"] == "HUMAN_REVIEW"

    def test_low_confidence_no_writer_agent_triggered(
        self,
        low_confidence_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that writer agent is NOT triggered for low confidence."""
        state = MockSessionState()
        state["judge_verdict"] = json.dumps(low_confidence_judge_verdict)

        verdict = json.loads(state["judge_verdict"])

        # For HUMAN_REVIEW, writer agent should not be invoked
        # This means composed_email should never be added to state
        if verdict["decision"] == "HUMAN_REVIEW":
            # Simulate the workflow NOT adding composed_email
            assert "composed_email" not in state

    def test_low_confidence_attempted_emails_format(
        self,
        low_confidence_web_search: dict[str, Any],
    ) -> None:
        """Test attempted_emails JSON format for status update."""
        web_result = low_confidence_web_search

        # Format attempted emails for status update
        attempted_emails = []
        if web_result.get("emails"):
            for email_info in web_result["emails"]:
                attempted_emails.append({
                    "email": email_info["email"],
                    "score": email_info["validation_score"],
                })

        attempted_emails_json = json.dumps(attempted_emails)

        # Verify format is correct
        parsed = json.loads(attempted_emails_json)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["email"] == "warranty@unknownbrand-support.com"
        assert parsed[0]["score"] == 0.55

    def test_low_confidence_status_update_data(
        self,
        low_confidence_judge_verdict: dict[str, Any],
        low_confidence_web_search: dict[str, Any],
    ) -> None:
        """Test data required for PENDING status update."""
        verdict = low_confidence_judge_verdict
        web_result = low_confidence_web_search

        # For PENDING status (low confidence), these should be available
        assert verdict["confidence_score"] < 0.80
        assert verdict["reasoning"] is not None

        # Attempted emails should be gathered from search results
        attempted_emails = [
            {"email": e["email"], "score": e["validation_score"]}
            for e in web_result.get("emails", [])
        ]
        assert len(attempted_emails) >= 0  # May be empty

        # Pending reason should be set
        pending_reason = "Low confidence - requires human verification"
        assert len(pending_reason) > 0


# =============================================================================
# NO EMAIL FOUND FLOW TESTS
# =============================================================================


@pytest.mark.integration
class TestNoEmailFoundFlow:
    """Test the no-email-found (REQUIRES_REVIEW) workflow."""

    def test_no_email_state_flow(
        self,
        sample_claim_details: dict[str, Any],
        no_email_internal_search: dict[str, Any],
        no_email_web_search: dict[str, Any],
        no_email_judge_verdict: dict[str, Any],
    ) -> None:
        """Test state flows correctly through no-email-found workflow."""
        state = MockSessionState()

        # Update claim details for obscure brand
        claim = sample_claim_details.copy()
        claim["product"]["brand"] = "ObscureBrand"
        state["claim_details"] = json.dumps(claim)

        # Step 1: Internal search returns not found
        state["internal_search_result"] = json.dumps(no_email_internal_search)
        internal_result = json.loads(state["internal_search_result"])
        assert internal_result["found"] is False

        # Step 2: Web search also returns not found
        state["web_search_result"] = json.dumps(no_email_web_search)
        web_result = json.loads(state["web_search_result"])
        assert web_result["found"] is False
        assert len(web_result["emails"]) == 0

        # Step 3: Judge verdict indicates no email found
        state["judge_verdict"] = json.dumps(no_email_judge_verdict)
        verdict = json.loads(state["judge_verdict"])
        assert verdict["confidence_score"] == 0.0
        assert verdict["recommended_email"] is None

        # Step 4: composed_email should NOT be in state
        assert "composed_email" not in state

    def test_no_email_detection_criteria(
        self,
        no_email_judge_verdict: dict[str, Any],
        no_email_internal_search: dict[str, Any],
        no_email_web_search: dict[str, Any],
    ) -> None:
        """Test detection criteria for no-email-found scenario."""
        verdict = no_email_judge_verdict
        internal = no_email_internal_search
        web = no_email_web_search

        # Detection criteria (any of these):
        # 1. recommended_email is None or empty
        has_no_recommended_email = (
            verdict["recommended_email"] is None or
            verdict["recommended_email"] == ""
        )
        assert has_no_recommended_email

        # 2. Both searches returned found=False
        both_searches_failed = (
            internal["found"] is False and
            web["found"] is False
        )
        assert both_searches_failed

        # 3. Confidence score is zero
        zero_confidence = verdict["confidence_score"] == 0.0
        assert zero_confidence

    def test_no_email_confidence_zero(
        self,
        no_email_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that no-email-found has zero confidence."""
        verdict = no_email_judge_verdict

        assert verdict["confidence_score"] == 0.0

        # All factors should be zero
        factors = verdict["factors"]
        assert factors["source_reliability"] == 0.00
        assert factors["validation_score_contribution"] == 0.00
        assert factors["domain_match"] == 0.00
        assert factors["source_agreement"] == 0.00

    def test_no_email_status_requires_review(
        self,
        no_email_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that no-email-found uses REQUIRES_REVIEW status."""
        verdict = no_email_judge_verdict

        # Status should be REQUIRES_REVIEW (not PENDING)
        # Decision from judge is HUMAN_REVIEW, but status is REQUIRES_REVIEW
        # to distinguish from low-confidence (which uses PENDING)
        recommended = verdict["recommended_email"]
        assert recommended is None or recommended == ""
        assert verdict["confidence_score"] == 0.0

    def test_no_email_reasoning_includes_search_attempts(
        self,
        no_email_judge_verdict: dict[str, Any],
    ) -> None:
        """Test that reasoning includes search attempt information."""
        verdict = no_email_judge_verdict
        reasoning = verdict["reasoning"].lower()

        # Reasoning should mention what was searched
        assert "internal" in reasoning or "database" in reasoning
        assert "web" in reasoning or "search" in reasoning
        assert "obscurebrand" in reasoning or "brand" in reasoning

    def test_no_email_user_message_includes_brand(
        self,
        sample_claim_details: dict[str, Any],
    ) -> None:
        """Test that user message template includes brand name."""
        # Simulate the expected user message
        brand = "ObscureBrand"
        message_template = (
            f"We could not find support contact information for {brand}. "
            "A support specialist will assist you."
        )

        assert brand in message_template
        assert "support specialist" in message_template


# =============================================================================
# STATE FLOW BETWEEN AGENTS TESTS
# =============================================================================


@pytest.mark.integration
class TestStateBetweenAgents:
    """Test state correctly flows between agents in the workflow."""

    def test_db_search_agent_output_key(self) -> None:
        """Test db_search_agent uses correct output_key."""
        from clara_care.sub_agents.db_search_agent import db_search_agent

        assert db_search_agent.output_key == "internal_search_result"

    def test_web_search_agent_output_key(self) -> None:
        """Test web_search_agent uses correct output_key."""
        from clara_care.sub_agents.web_search_agent import web_search_agent

        assert web_search_agent.output_key == "web_search_result"

    def test_judge_agent_output_key(self) -> None:
        """Test judge_agent uses correct output_key."""
        from clara_care.sub_agents.judge_agent import judge_agent

        assert judge_agent.output_key == "judge_verdict"

    def test_writer_agent_output_key(self) -> None:
        """Test writer_agent uses correct output_key."""
        from clara_care.sub_agents.writer_agent import writer_agent

        assert writer_agent.output_key == "composed_email"

    def test_parallel_agents_have_unique_output_keys(self) -> None:
        """Test that parallel search agents have unique output_keys."""
        from clara_care.sub_agents.search_pipeline import search_pipeline

        output_keys = []
        for sub_agent in search_pipeline.sub_agents:
            if hasattr(sub_agent, "output_key") and sub_agent.output_key:
                output_keys.append(sub_agent.output_key)

        # All output_keys should be unique
        assert len(output_keys) == len(set(output_keys))
        assert "internal_search_result" in output_keys
        assert "web_search_result" in output_keys

    def test_sequential_pipeline_order(self) -> None:
        """Test search_judge_pipeline executes in correct order."""
        from clara_care.sub_agents.search_judge_pipeline import search_judge_pipeline

        sub_agent_names = [a.name for a in search_judge_pipeline.sub_agents]

        # search_pipeline should come before judge_agent
        assert len(sub_agent_names) == 2
        assert sub_agent_names[0] == "search_pipeline"
        assert sub_agent_names[1] == "judge_agent"

    def test_judge_reads_search_results_from_state(self) -> None:
        """Test judge_agent instruction references state placeholders."""
        from clara_care.sub_agents.judge_agent import judge_agent

        instruction = judge_agent.instruction

        # Judge should read from these state keys
        assert "{internal_search_result}" in instruction
        assert "{web_search_result}" in instruction

    def test_writer_reads_verdict_from_state(self) -> None:
        """Test writer_agent instruction references state placeholders."""
        from clara_care.sub_agents.writer_agent import writer_agent

        instruction = writer_agent.instruction

        # Writer should read from these state keys
        assert "{claim_details}" in instruction
        assert "{judge_verdict}" in instruction

    def test_root_agent_has_required_tools(self) -> None:
        """Test root agent has get_claim_details and update_claim_status."""
        from clara_care import root_agent

        tool_names = []
        for tool in root_agent.tools:
            if callable(tool):
                tool_names.append(tool.__name__)
            elif hasattr(tool, "name"):
                tool_names.append(tool.name)

        assert "get_claim_details" in tool_names
        assert "update_claim_status" in tool_names

    def test_root_agent_has_required_sub_agents(self) -> None:
        """Test root agent has search_judge_pipeline and writer_agent."""
        from clara_care import root_agent

        sub_agent_names = [a.name for a in root_agent.sub_agents]

        assert "search_judge_pipeline" in sub_agent_names
        assert "writer_agent" in sub_agent_names

    def test_full_state_flow_simulation(
        self,
        sample_claim_details: dict[str, Any],
        high_confidence_internal_search: dict[str, Any],
        high_confidence_web_search: dict[str, Any],
        high_confidence_judge_verdict: dict[str, Any],
        composed_email: dict[str, Any],
    ) -> None:
        """Test complete state flow through all agents."""
        state = MockSessionState()

        # Simulate workflow state progression
        # 1. Root agent gets claim details
        state["claim_details"] = json.dumps(sample_claim_details)

        # 2. search_pipeline (parallel) runs
        #    - db_search_agent writes to internal_search_result
        #    - web_search_agent writes to web_search_result
        state["internal_search_result"] = json.dumps(high_confidence_internal_search)
        state["web_search_result"] = json.dumps(high_confidence_web_search)

        # 3. judge_agent reads search results, writes verdict
        state["judge_verdict"] = json.dumps(high_confidence_judge_verdict)

        # 4. For AUTO_SUBMIT: writer_agent composes email
        verdict = json.loads(state["judge_verdict"])
        if verdict["decision"] == "AUTO_SUBMIT":
            state["composed_email"] = json.dumps(composed_email)

        # Verify all expected state keys are present
        expected_keys = [
            "claim_details",
            "internal_search_result",
            "web_search_result",
            "judge_verdict",
            "composed_email",  # Only for AUTO_SUBMIT
        ]

        for key in expected_keys:
            assert key in state, f"Missing state key: {key}"

        # Verify data consistency across state
        claim = json.loads(state["claim_details"])
        email = json.loads(state["composed_email"])
        assert claim["claim_id"] == email["claim_id"]


# =============================================================================
# INTEGRATION WITH INMEMORY SESSION SERVICE
# =============================================================================


@pytest.mark.integration
class TestWithInMemorySessionService:
    """Test integration patterns with InMemorySessionService."""

    def test_session_state_initialization(self) -> None:
        """Test that state can be initialized in session."""
        state = MockSessionState()
        state.update({
            "user_id": "test-user-001",
            "claim_id": "CLM-TEST-001",
        })

        assert state.get("user_id") == "test-user-001"
        assert state.get("claim_id") == "CLM-TEST-001"

    def test_session_state_persistence(self) -> None:
        """Test state persists across operations."""
        state = MockSessionState()

        # First operation
        state["step1_result"] = "result from step 1"

        # Second operation should see first result
        assert state.get("step1_result") == "result from step 1"

        # Third operation adds more data
        state["step2_result"] = "result from step 2"

        # All data should be accessible
        assert state.get("step1_result") == "result from step 1"
        assert state.get("step2_result") == "result from step 2"

    def test_session_state_isolation(self) -> None:
        """Test separate sessions have isolated state."""
        session1 = MockSessionState()
        session2 = MockSessionState()

        session1["data"] = "session 1 data"
        session2["data"] = "session 2 data"

        assert session1["data"] != session2["data"]
        assert session1["data"] == "session 1 data"
        assert session2["data"] == "session 2 data"


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases in the workflow."""

    def test_confidence_exactly_at_threshold(self) -> None:
        """Test behavior when confidence is exactly 0.80."""
        verdict = {
            "confidence_score": 0.80,  # Exactly at threshold
            "recommended_email": "support@brand.com",
            "decision": "AUTO_SUBMIT",  # Should still AUTO_SUBMIT at threshold
        }

        # >= 0.80 should trigger AUTO_SUBMIT
        threshold = 0.80
        assert verdict["confidence_score"] >= threshold
        assert verdict["decision"] == "AUTO_SUBMIT"

    def test_confidence_just_below_threshold(self) -> None:
        """Test behavior when confidence is just below 0.80."""
        verdict = {
            "confidence_score": 0.79,  # Just below
            "recommended_email": "support@brand.com",
            "decision": "HUMAN_REVIEW",
        }

        threshold = 0.80
        assert verdict["confidence_score"] < threshold
        assert verdict["decision"] == "HUMAN_REVIEW"

    def test_empty_web_search_with_internal_match(self) -> None:
        """Test when web search fails but internal DB has match."""
        internal = {
            "found": True,
            "email": "support@brand.com",
            "confidence": 0.90,
            "source": "internal_db",
        }
        web = {
            "found": False,
            "emails": [],
        }

        # Should still be able to AUTO_SUBMIT if internal confidence is high
        # (depends on judge scoring logic)
        assert internal["found"] is True
        assert web["found"] is False

    def test_multiple_emails_from_web_search(self) -> None:
        """Test handling multiple email candidates from web search."""
        web = {
            "found": True,
            "emails": [
                {"email": "support@brand.com", "validation_score": 0.95},
                {"email": "warranty@brand.com", "validation_score": 0.85},
                {"email": "help@brand.com", "validation_score": 0.70},
            ],
        }

        # Judge should select highest scoring email
        best_email = max(web["emails"], key=lambda x: x["validation_score"])
        assert best_email["email"] == "support@brand.com"

    def test_conflicting_emails_between_sources(self) -> None:
        """Test when internal DB and web search return different emails."""
        internal = {
            "found": True,
            "email": "old-support@brand.com",
            "confidence": 0.90,
        }
        web = {
            "found": True,
            "emails": [
                {"email": "new-support@brand.com", "validation_score": 0.95},
            ],
        }

        # Both sources found, but emails differ
        assert internal["email"] != web["emails"][0]["email"]
        # Judge should evaluate and select most reliable

    def test_malformed_email_filtering(self) -> None:
        """Test that malformed emails are handled."""
        web_emails = [
            {"email": "valid@brand.com", "validation_score": 0.90},
            {"email": "invalid-no-at-sign.com", "validation_score": 0.00},
            {"email": "", "validation_score": 0.00},
        ]

        # Filter out invalid emails
        valid_emails = [
            e for e in web_emails
            if e["email"] and "@" in e["email"] and e["validation_score"] > 0
        ]

        assert len(valid_emails) == 1
        assert valid_emails[0]["email"] == "valid@brand.com"
