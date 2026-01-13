"""Unit tests for ClaraCare tools.

This module tests all tool functions with mock data and fixtures.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# Fixtures for mock ToolContext
# ==============================================================================


class MockToolContextState:
    """Mock state object for ToolContext."""

    def __init__(self, state_dict: dict[str, Any] | None = None):
        self._state = state_dict or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._state[key]


class MockToolContext:
    """Mock ToolContext for testing tools that require context."""

    def __init__(self, state_dict: dict[str, Any] | None = None):
        self.state = MockToolContextState(state_dict)


@pytest.fixture
def mock_tool_context() -> MockToolContext:
    """Fixture providing a mock ToolContext with default state."""
    return MockToolContext({"user_id": "test-user-123"})


@pytest.fixture
def mock_tool_context_with_search_results() -> MockToolContext:
    """Fixture providing mock ToolContext with web search results."""
    return MockToolContext({
        "user_id": "test-user-123",
        "web_search_raw_results": (
            "Contact Sony Support at support@sony.com for warranty claims. "
            "You can also reach out to warranty@sony.co.uk or call 1-800-SONY."
        ),
        "web_search_source_urls": ["https://www.sony.com/support"],
    })


# ==============================================================================
# Tests for search_support_contacts (db_search.py)
# ==============================================================================


class TestSearchSupportContacts:
    """Tests for the search_support_contacts tool."""

    @pytest.fixture
    def mock_supabase_response_found(self) -> MagicMock:
        """Mock Supabase response with found results."""
        response = MagicMock()
        response.data = [
            {
                "brand_name": "Sony",
                "support_email": "support@sony.com",
                "support_phone": "1-800-222-7669",
                "support_url": "https://www.sony.com/support",
                "confidence_score": 0.95,
                "source": "official_website",
                "product_category": "Electronics",
            }
        ]
        return response

    @pytest.fixture
    def mock_supabase_response_not_found(self) -> MagicMock:
        """Mock Supabase response with no results."""
        response = MagicMock()
        response.data = []
        return response

    @pytest.fixture
    def mock_supabase_response_multiple(self) -> MagicMock:
        """Mock Supabase response with multiple results."""
        response = MagicMock()
        response.data = [
            {
                "brand_name": "Samsung Electronics",
                "support_email": "support@samsung.com",
                "support_phone": "1-800-726-7864",
                "support_url": "https://www.samsung.com/support",
                "confidence_score": 0.92,
                "source": "official_website",
                "product_category": "Electronics",
            },
            {
                "brand_name": "Samsung Appliances",
                "support_email": "appliances@samsung.com",
                "support_phone": "1-800-726-7864",
                "support_url": "https://www.samsung.com/appliances/support",
                "confidence_score": 0.88,
                "source": "official_website",
                "product_category": "Appliances",
            },
        ]
        return response

    def test_search_support_contacts_found(
        self,
        mock_supabase_response_found: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test searching for contacts that exist in the database."""
        with patch(
            "clara_care.tools.db_search.get_client"
        ) as mock_get_client:
            # Setup mock client chain
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_ilike = MagicMock()
            mock_ilike2 = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.ilike.return_value = mock_ilike
            # Handle second ilike call for category filter
            mock_ilike.ilike.return_value = mock_ilike2
            mock_ilike2.execute.return_value = mock_supabase_response_found

            from clara_care.tools.db_search import search_support_contacts

            result = search_support_contacts(
                brand_name="Sony",
                product_category="Electronics",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["brand_name"] == "Sony"
            assert result_data["results"][0]["support_email"] == "support@sony.com"
            assert result_data["results"][0]["confidence_score"] == 0.95
            assert "Found 1 support contact" in result_data["message"]

    def test_search_support_contacts_not_found(
        self,
        mock_supabase_response_not_found: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test searching for contacts that don't exist."""
        with patch(
            "clara_care.tools.db_search.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_ilike = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.ilike.return_value = mock_ilike
            mock_ilike.execute.return_value = mock_supabase_response_not_found

            from clara_care.tools.db_search import search_support_contacts

            result = search_support_contacts(
                brand_name="UnknownBrand",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is False
            assert len(result_data["results"]) == 0
            assert "No support contacts found" in result_data["message"]

    def test_search_support_contacts_empty_brand_name(self) -> None:
        """Test that empty brand name returns an error."""
        from clara_care.tools.db_search import search_support_contacts

        result = search_support_contacts(brand_name="")
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert "brand_name is required" in result_data["message"]

    def test_search_support_contacts_whitespace_brand_name(self) -> None:
        """Test that whitespace-only brand name returns an error."""
        from clara_care.tools.db_search import search_support_contacts

        result = search_support_contacts(brand_name="   ")
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert "brand_name is required" in result_data["message"]

    def test_search_support_contacts_multiple_results(
        self,
        mock_supabase_response_multiple: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test searching returns multiple matching contacts."""
        with patch(
            "clara_care.tools.db_search.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_ilike = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.ilike.return_value = mock_ilike
            mock_ilike.execute.return_value = mock_supabase_response_multiple

            from clara_care.tools.db_search import search_support_contacts

            result = search_support_contacts(
                brand_name="Samsung",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is True
            assert len(result_data["results"]) == 2
            assert "Found 2 support contact" in result_data["message"]

    def test_search_support_contacts_connection_error(
        self,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test handling of database connection errors."""
        with patch(
            "clara_care.tools.db_search.get_client"
        ) as mock_get_client:
            from clara_care.supabase_client import SupabaseConnectionError

            mock_get_client.side_effect = SupabaseConnectionError("Connection failed")

            from clara_care.tools.db_search import search_support_contacts

            result = search_support_contacts(
                brand_name="Sony",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is False
            assert result_data.get("error") is True
            assert "Database connection error" in result_data["message"]

    def test_search_support_contacts_without_tool_context(
        self,
        mock_supabase_response_found: MagicMock,
    ) -> None:
        """Test that tool works without ToolContext."""
        with patch(
            "clara_care.tools.db_search.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_ilike = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.ilike.return_value = mock_ilike
            mock_ilike.execute.return_value = mock_supabase_response_found

            from clara_care.tools.db_search import search_support_contacts

            result = search_support_contacts(brand_name="Sony")
            result_data = json.loads(result)
            assert result_data["found"] is True

    def test_search_support_contacts_with_category_filter(
        self,
        mock_supabase_response_found: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test that category filter is applied."""
        with patch(
            "clara_care.tools.db_search.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_ilike = MagicMock()
            mock_ilike2 = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.ilike.return_value = mock_ilike
            mock_ilike.ilike.return_value = mock_ilike2
            mock_ilike2.execute.return_value = mock_supabase_response_found

            from clara_care.tools.db_search import search_support_contacts

            result = search_support_contacts(
                brand_name="Sony",
                product_category="Electronics",
                tool_context=mock_tool_context,
            )

            # Verify that ilike was called twice (for brand and category)
            result_data = json.loads(result)
            assert result_data["found"] is True
            assert "Electronics" in result_data["message"]


# ==============================================================================
# Tests for search_support_email (web_search.py)
# ==============================================================================


class TestSearchSupportEmail:
    """Tests for the search_support_email tool and helpers."""

    def test_extract_emails_from_text_single(self) -> None:
        """Test extracting a single email from text."""
        from clara_care.tools.web_search import extract_emails_from_text

        text = "Contact us at support@example.com for help."
        emails = extract_emails_from_text(text)
        assert emails == ["support@example.com"]

    def test_extract_emails_from_text_multiple(self) -> None:
        """Test extracting multiple emails from text."""
        from clara_care.tools.web_search import extract_emails_from_text

        text = "Email support@example.com or sales@example.com for assistance."
        emails = extract_emails_from_text(text)
        assert len(emails) == 2
        assert "support@example.com" in emails
        assert "sales@example.com" in emails

    def test_extract_emails_from_text_duplicates(self) -> None:
        """Test that duplicate emails are deduplicated."""
        from clara_care.tools.web_search import extract_emails_from_text

        text = "Email support@example.com. Again: support@example.com"
        emails = extract_emails_from_text(text)
        assert len(emails) == 1
        assert emails[0] == "support@example.com"

    def test_extract_emails_from_text_case_insensitive(self) -> None:
        """Test that emails are lowercased."""
        from clara_care.tools.web_search import extract_emails_from_text

        text = "Email SUPPORT@EXAMPLE.COM for help."
        emails = extract_emails_from_text(text)
        assert emails == ["support@example.com"]

    def test_extract_emails_from_text_empty(self) -> None:
        """Test extracting from empty text."""
        from clara_care.tools.web_search import extract_emails_from_text

        assert extract_emails_from_text("") == []
        assert extract_emails_from_text("no emails here") == []

    def test_validate_email_format_valid(self) -> None:
        """Test validating valid email formats."""
        from clara_care.tools.web_search import validate_email_format

        assert validate_email_format("support@example.com") is True
        assert validate_email_format("user.name@domain.co.uk") is True
        assert validate_email_format("a@b.io") is True

    def test_validate_email_format_invalid(self) -> None:
        """Test validating invalid email formats."""
        from clara_care.tools.web_search import validate_email_format

        assert validate_email_format("") is False
        assert validate_email_format("invalid") is False
        assert validate_email_format("@nodomain.com") is False
        assert validate_email_format("no@") is False
        assert validate_email_format("..bad@example.com") is False

    def test_search_support_email_empty_brand(self) -> None:
        """Test that empty brand name returns an error."""
        from clara_care.tools.web_search import search_support_email

        result = search_support_email(brand_name="")
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert "brand_name is required" in result_data["message"]

    def test_search_support_email_no_search_results(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test when no search results are provided in state."""
        from clara_care.tools.web_search import search_support_email

        result = search_support_email(
            brand_name="Sony",
            tool_context=mock_tool_context,
        )
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert result_data["search_query"] == "Sony warranty support email contact"
        assert "google_search" in result_data["message"]

    def test_search_support_email_with_search_results(
        self, mock_tool_context_with_search_results: MockToolContext,
    ) -> None:
        """Test when search results are provided in state."""
        from clara_care.tools.web_search import search_support_email

        result = search_support_email(
            brand_name="Sony",
            tool_context=mock_tool_context_with_search_results,
        )
        result_data = json.loads(result)
        assert result_data["found"] is True
        assert len(result_data["emails"]) >= 1

        # Check that sony.com emails are found
        found_emails = [e["email"] for e in result_data["emails"]]
        assert "support@sony.com" in found_emails

    def test_search_support_email_with_product_type(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test search query includes product type."""
        from clara_care.tools.web_search import search_support_email

        result = search_support_email(
            brand_name="Sony",
            product_type="TV",
            tool_context=mock_tool_context,
        )
        result_data = json.loads(result)
        assert "TV" in result_data["search_query"]

    def test_parse_search_results_for_emails_found(self) -> None:
        """Test parsing search results with emails."""
        from clara_care.tools.web_search import parse_search_results_for_emails

        search_text = (
            "Contact Sony Support at support@sony.com or warranty@sony.com "
            "for warranty claims."
        )
        result = parse_search_results_for_emails(
            search_results=search_text,
            brand_name="Sony",
        )
        result_data = json.loads(result)
        assert result_data["found"] is True
        assert result_data["count"] == 2

        # Check domain matching
        emails_data = result_data["emails"]
        assert any(e["domain_matches_brand"] for e in emails_data)

    def test_parse_search_results_for_emails_not_found(self) -> None:
        """Test parsing search results with no emails."""
        from clara_care.tools.web_search import parse_search_results_for_emails

        result = parse_search_results_for_emails(
            search_results="No contact information available.",
            brand_name="Sony",
        )
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert result_data["count"] == 0

    def test_parse_search_results_for_emails_empty_input(self) -> None:
        """Test parsing empty search results."""
        from clara_care.tools.web_search import parse_search_results_for_emails

        result = parse_search_results_for_emails(search_results="")
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert "search_results is required" in result_data["message"]

    def test_parse_search_results_support_related_detection(self) -> None:
        """Test that support-related emails are flagged."""
        from clara_care.tools.web_search import parse_search_results_for_emails

        search_text = "Email support@example.com or marketing@example.com"
        result = parse_search_results_for_emails(
            search_results=search_text,
            brand_name="example",
        )
        result_data = json.loads(result)

        support_emails = [
            e for e in result_data["emails"] if e["is_support_related"]
        ]
        non_support_emails = [
            e for e in result_data["emails"] if not e["is_support_related"]
        ]

        assert len(support_emails) == 1
        assert support_emails[0]["email"] == "support@example.com"
        assert len(non_support_emails) == 1


# ==============================================================================
# Tests for validate_email (email_validator.py)
# ==============================================================================


class TestValidateEmail:
    """Tests for the validate_email tool and helpers."""

    def test_check_email_format_valid(self) -> None:
        """Test format checking with valid emails."""
        from clara_care.tools.email_validator import check_email_format

        is_valid, issues = check_email_format("user@example.com")
        assert is_valid is True
        assert issues == []

    def test_check_email_format_invalid_empty(self) -> None:
        """Test format checking with empty email."""
        from clara_care.tools.email_validator import check_email_format

        is_valid, issues = check_email_format("")
        assert is_valid is False
        assert "Email is empty" in issues

    def test_check_email_format_invalid_no_at(self) -> None:
        """Test format checking without @ symbol."""
        from clara_care.tools.email_validator import check_email_format

        is_valid, issues = check_email_format("nodomain.com")
        assert is_valid is False

    def test_check_email_format_invalid_consecutive_dots(self) -> None:
        """Test format checking with consecutive dots."""
        from clara_care.tools.email_validator import check_email_format

        is_valid, issues = check_email_format("user..name@example.com")
        assert is_valid is False
        assert any("consecutive periods" in issue for issue in issues)

    def test_check_domain_matches_brand_exact(self) -> None:
        """Test exact brand domain match."""
        from clara_care.tools.email_validator import check_domain_matches_brand

        matches, confidence, reason = check_domain_matches_brand(
            "support@sony.com", "Sony"
        )
        assert matches is True
        assert confidence == 1.0
        assert "exactly matches" in reason

    def test_check_domain_matches_brand_contains(self) -> None:
        """Test brand contained in domain."""
        from clara_care.tools.email_validator import check_domain_matches_brand

        matches, confidence, reason = check_domain_matches_brand(
            "support@support.sony.com", "Sony"
        )
        assert matches is True
        assert confidence == 0.9

    def test_check_domain_matches_brand_no_match(self) -> None:
        """Test brand not matching domain."""
        from clara_care.tools.email_validator import check_domain_matches_brand

        matches, confidence, reason = check_domain_matches_brand(
            "support@example.com", "Sony"
        )
        assert matches is False
        assert confidence == 0.0

    def test_detect_suspicious_patterns_free_email(self) -> None:
        """Test detection of free email providers."""
        from clara_care.tools.email_validator import detect_suspicious_patterns

        flags, penalty = detect_suspicious_patterns("user@gmail.com")
        assert any("Free email provider" in f for f in flags)
        assert penalty >= 0.4

    def test_detect_suspicious_patterns_suspicious_tld(self) -> None:
        """Test detection of suspicious TLDs."""
        from clara_care.tools.email_validator import detect_suspicious_patterns

        flags, penalty = detect_suspicious_patterns("user@fake-support.xyz")
        assert any(".xyz" in f for f in flags)
        assert penalty >= 0.3

    def test_detect_suspicious_patterns_numeric_domain(self) -> None:
        """Test detection of numeric domains."""
        from clara_care.tools.email_validator import detect_suspicious_patterns

        flags, penalty = detect_suspicious_patterns("user@domain12345.com")
        assert any("numbers" in f for f in flags)
        assert penalty >= 0.2

    def test_detect_suspicious_patterns_noreply(self) -> None:
        """Test detection of no-reply addresses."""
        from clara_care.tools.email_validator import detect_suspicious_patterns

        flags, penalty = detect_suspicious_patterns("noreply@example.com")
        assert any("No-reply" in f for f in flags)

    def test_detect_suspicious_patterns_clean(self) -> None:
        """Test clean email with no suspicious patterns."""
        from clara_care.tools.email_validator import detect_suspicious_patterns

        flags, penalty = detect_suspicious_patterns("support@sony.com")
        assert len(flags) == 0
        assert penalty == 0.0

    def test_calculate_validation_score_perfect(self) -> None:
        """Test score calculation for perfect email."""
        from clara_care.tools.email_validator import calculate_validation_score

        score = calculate_validation_score(
            format_valid=True,
            domain_exists=True,
            domain_matches_brand=True,
            brand_match_confidence=1.0,
            suspicion_penalty=0.0,
        )
        # 0.5 (base) + 0.2 (domain) + 0.3 * 1.0 (brand) = 1.0
        assert score == 1.0

    def test_calculate_validation_score_invalid_format(self) -> None:
        """Test that invalid format gives zero score."""
        from clara_care.tools.email_validator import calculate_validation_score

        score = calculate_validation_score(
            format_valid=False,
            domain_exists=True,
            domain_matches_brand=True,
            brand_match_confidence=1.0,
            suspicion_penalty=0.0,
        )
        assert score == 0.0

    def test_calculate_validation_score_with_penalty(self) -> None:
        """Test score calculation with suspicion penalty."""
        from clara_care.tools.email_validator import calculate_validation_score

        score = calculate_validation_score(
            format_valid=True,
            domain_exists=True,
            domain_matches_brand=True,
            brand_match_confidence=1.0,
            suspicion_penalty=0.5,
        )
        # (0.5 + 0.2 + 0.3) * (1 - 0.5) = 0.5
        assert score == 0.5

    def test_validate_email_full_valid(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test full validation of a valid email."""
        from clara_care.tools.email_validator import validate_email

        # Patch MX check to avoid network calls
        with patch(
            "clara_care.tools.email_validator.check_domain_mx_records"
        ) as mock_mx:
            mock_mx.return_value = (True, "Found MX records")

            result = validate_email(
                email="support@sony.com",
                brand_name="Sony",
                check_mx=True,
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["is_valid"] is True
            assert result_data["format_valid"] is True
            assert result_data["domain_exists"] is True
            assert result_data["domain_matches_brand"] is True
            assert result_data["validation_score"] >= 0.7

    def test_validate_email_empty(self) -> None:
        """Test validation of empty email."""
        from clara_care.tools.email_validator import validate_email

        result = validate_email(email="")
        result_data = json.loads(result)
        assert result_data["is_valid"] is False
        assert result_data["validation_score"] == 0.0
        assert "email is required" in result_data["message"]

    def test_validate_email_invalid_format(self) -> None:
        """Test validation of invalid format email."""
        from clara_care.tools.email_validator import validate_email

        result = validate_email(email="not-an-email")
        result_data = json.loads(result)
        assert result_data["is_valid"] is False
        assert result_data["format_valid"] is False
        assert result_data["validation_score"] == 0.0

    def test_validate_email_free_provider(self) -> None:
        """Test validation of free email provider."""
        from clara_care.tools.email_validator import validate_email

        with patch(
            "clara_care.tools.email_validator.check_domain_mx_records"
        ) as mock_mx:
            mock_mx.return_value = (True, "Found MX records")

            result = validate_email(
                email="user@gmail.com",
                brand_name="Sony",
                check_mx=True,
            )

            result_data = json.loads(result)
            # Should be valid format but have suspicion flags
            assert result_data["format_valid"] is True
            assert "Free email provider" in str(result_data["suspicion_flags"])
            # Score should be lower due to penalty
            assert result_data["validation_score"] < 0.5

    def test_validate_email_no_mx_check(self) -> None:
        """Test validation without MX check."""
        from clara_care.tools.email_validator import validate_email

        result = validate_email(
            email="support@sony.com",
            brand_name="Sony",
            check_mx=False,
        )

        result_data = json.loads(result)
        assert result_data["format_valid"] is True
        assert "Skipped - MX check disabled" in result_data["domain_check_message"]

    def test_validate_email_without_brand(self) -> None:
        """Test validation without brand matching."""
        from clara_care.tools.email_validator import validate_email

        with patch(
            "clara_care.tools.email_validator.check_domain_mx_records"
        ) as mock_mx:
            mock_mx.return_value = (True, "Found MX records")

            result = validate_email(
                email="support@example.com",
                brand_name="",
                check_mx=True,
            )

            result_data = json.loads(result)
            assert result_data["format_valid"] is True
            assert "no brand name provided" in result_data["brand_match_reasoning"]


# ==============================================================================
# Tests for update_claim_status (claim_status.py)
# ==============================================================================


class TestUpdateClaimStatus:
    """Tests for the update_claim_status tool."""

    @pytest.fixture
    def mock_supabase_update_success(self) -> MagicMock:
        """Mock Supabase response for successful update."""
        response = MagicMock()
        response.data = [{"id": "claim-123", "status": "SUBMITTED"}]
        return response

    @pytest.fixture
    def mock_supabase_update_not_found(self) -> MagicMock:
        """Mock Supabase response when claim not found."""
        response = MagicMock()
        response.data = []
        return response

    def test_update_claim_status_submitted(
        self,
        mock_supabase_update_success: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test updating claim status to SUBMITTED."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_insert = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.update.return_value = mock_update
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_update_success
            mock_table.insert.return_value = mock_insert
            mock_insert.execute.return_value = MagicMock(data=[{}])

            from clara_care.tools.claim_status import update_claim_status

            result = update_claim_status(
                claim_id="claim-123",
                status="SUBMITTED",
                support_email_used="support@sony.com",
                confidence_score=0.95,
                judge_reasoning="High confidence from internal DB",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["claim_id"] == "claim-123"
            assert result_data["status"] == "SUBMITTED"
            assert "updated_at" in result_data

    def test_update_claim_status_pending(
        self,
        mock_supabase_update_success: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test updating claim status to PENDING with low confidence."""
        mock_supabase_update_success.data = [{"id": "claim-123", "status": "PENDING"}]

        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_insert = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.update.return_value = mock_update
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_update_success
            mock_table.insert.return_value = mock_insert
            mock_insert.execute.return_value = MagicMock(data=[{}])

            from clara_care.tools.claim_status import update_claim_status

            result = update_claim_status(
                claim_id="claim-123",
                status="PENDING",
                confidence_score=0.65,
                judge_reasoning="Low confidence from web search",
                attempted_emails='[{"email": "help@brand.com", "score": 0.65}]',
                pending_reason="Low confidence - requires human verification",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["status"] == "PENDING"

    def test_update_claim_status_requires_review(
        self,
        mock_supabase_update_success: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test updating claim status to REQUIRES_REVIEW."""
        mock_supabase_update_success.data = [
            {"id": "claim-123", "status": "REQUIRES_REVIEW"}
        ]

        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_insert = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.update.return_value = mock_update
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_update_success
            mock_table.insert.return_value = mock_insert
            mock_insert.execute.return_value = MagicMock(data=[{}])

            from clara_care.tools.claim_status import update_claim_status

            result = update_claim_status(
                claim_id="claim-123",
                status="REQUIRES_REVIEW",
                confidence_score=0.0,
                judge_reasoning="No email found for brand",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["status"] == "REQUIRES_REVIEW"

    def test_update_claim_status_invalid_status(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test updating with invalid status value."""
        from clara_care.tools.claim_status import update_claim_status

        result = update_claim_status(
            claim_id="claim-123",
            status="INVALID_STATUS",
            tool_context=mock_tool_context,
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Invalid status" in result_data["message"]
        assert "PENDING" in result_data["message"]  # Shows valid options

    def test_update_claim_status_empty_claim_id(self) -> None:
        """Test updating with empty claim_id."""
        from clara_care.tools.claim_status import update_claim_status

        result = update_claim_status(claim_id="", status="SUBMITTED")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "claim_id is required" in result_data["message"]

    def test_update_claim_status_claim_not_found(
        self,
        mock_supabase_update_not_found: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test updating claim that doesn't exist."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_update = MagicMock()
            mock_eq = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.update.return_value = mock_update
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_update_not_found

            from clara_care.tools.claim_status import update_claim_status

            result = update_claim_status(
                claim_id="nonexistent-claim",
                status="SUBMITTED",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "not found" in result_data["message"]

    def test_update_claim_status_connection_error(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test handling of database connection errors."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            from clara_care.supabase_client import SupabaseConnectionError

            mock_get_client.side_effect = SupabaseConnectionError("Connection failed")

            from clara_care.tools.claim_status import update_claim_status

            result = update_claim_status(
                claim_id="claim-123",
                status="SUBMITTED",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert result_data.get("error") is True

    def test_update_claim_status_case_insensitive(
        self,
        mock_supabase_update_success: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test that status is case-insensitive."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_insert = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.update.return_value = mock_update
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_update_success
            mock_table.insert.return_value = mock_insert
            mock_insert.execute.return_value = MagicMock(data=[{}])

            from clara_care.tools.claim_status import update_claim_status

            result = update_claim_status(
                claim_id="claim-123",
                status="submitted",  # lowercase
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["status"] == "SUBMITTED"


class TestGetClaimStatus:
    """Tests for the get_claim_status tool."""

    @pytest.fixture
    def mock_supabase_claim_found(self) -> MagicMock:
        """Mock Supabase response with found claim."""
        response = MagicMock()
        response.data = [{
            "id": "claim-123",
            "status": "SUBMITTED",
            "support_email_used": "support@sony.com",
            "confidence_score": 0.95,
            "judge_reasoning": "High confidence",
            "updated_at": "2026-01-13T10:30:00Z",
            "created_at": "2026-01-13T10:00:00Z",
        }]
        return response

    def test_get_claim_status_found(
        self,
        mock_supabase_claim_found: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test retrieving existing claim status."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_claim_found

            from clara_care.tools.claim_status import get_claim_status

            result = get_claim_status(
                claim_id="claim-123",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is True
            assert result_data["claim"]["id"] == "claim-123"
            assert result_data["claim"]["status"] == "SUBMITTED"

    def test_get_claim_status_with_history(
        self,
        mock_supabase_claim_found: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test retrieving claim status with history."""
        mock_history_response = MagicMock()
        mock_history_response.data = [
            {
                "status": "SUBMITTED",
                "support_email_used": "support@sony.com",
                "confidence_score": 0.95,
                "judge_reasoning": "High confidence",
                "created_at": "2026-01-13T10:30:00Z",
                "created_by": "test-user-123",
            },
            {
                "status": "PENDING",
                "support_email_used": None,
                "confidence_score": None,
                "judge_reasoning": None,
                "created_at": "2026-01-13T10:00:00Z",
                "created_by": "system",
            },
        ]

        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            mock_order = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_claim_found
            mock_eq.order.return_value = mock_order
            mock_order.execute.return_value = mock_history_response

            from clara_care.tools.claim_status import get_claim_status

            result = get_claim_status(
                claim_id="claim-123",
                include_history=True,
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is True
            assert len(result_data["history"]) == 2

    def test_get_claim_status_not_found(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test retrieving non-existent claim."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()

            mock_response = MagicMock()
            mock_response.data = []

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response

            from clara_care.tools.claim_status import get_claim_status

            result = get_claim_status(
                claim_id="nonexistent",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is False
            assert "not found" in result_data["message"]

    def test_get_claim_status_empty_claim_id(self) -> None:
        """Test with empty claim_id."""
        from clara_care.tools.claim_status import get_claim_status

        result = get_claim_status(claim_id="")
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert "claim_id is required" in result_data["message"]


class TestGetClaimDetails:
    """Tests for the get_claim_details tool."""

    @pytest.fixture
    def mock_supabase_claim_details(self) -> MagicMock:
        """Mock Supabase response with full claim details."""
        response = MagicMock()
        response.data = [{
            "id": "CLM-12345",
            "status": "PENDING",
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "user_phone": "555-1234",
            "product_brand": "Sony",
            "product_name": "Bravia TV",
            "product_category": "Electronics",
            "product_serial_number": "SN123456",
            "purchase_date": "2025-06-15",
            "issue_description": "Screen flickering",
            "issue_occurrence_date": "2026-01-10",
            "receipt_reference": "REC-789",
            "created_at": "2026-01-12T10:00:00Z",
            "updated_at": "2026-01-12T10:00:00Z",
        }]
        return response

    def test_get_claim_details_found(
        self,
        mock_supabase_claim_details: MagicMock,
        mock_tool_context: MockToolContext,
    ) -> None:
        """Test retrieving full claim details."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_supabase_claim_details

            from clara_care.tools.claim_status import get_claim_details

            result = get_claim_details(
                claim_id="CLM-12345",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is True
            assert result_data["claim_id"] == "CLM-12345"
            assert result_data["user"]["name"] == "John Doe"
            assert result_data["product"]["brand"] == "Sony"
            assert result_data["issue"]["description"] == "Screen flickering"

    def test_get_claim_details_not_found(
        self, mock_tool_context: MockToolContext,
    ) -> None:
        """Test retrieving non-existent claim details."""
        with patch(
            "clara_care.tools.claim_status.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()

            mock_response = MagicMock()
            mock_response.data = []

            mock_get_client.return_value = mock_client
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response

            from clara_care.tools.claim_status import get_claim_details

            result = get_claim_details(
                claim_id="nonexistent",
                tool_context=mock_tool_context,
            )

            result_data = json.loads(result)
            assert result_data["found"] is False

    def test_get_claim_details_empty_claim_id(self) -> None:
        """Test with empty claim_id."""
        from clara_care.tools.claim_status import get_claim_details

        result = get_claim_details(claim_id="")
        result_data = json.loads(result)
        assert result_data["found"] is False
        assert "claim_id is required" in result_data["message"]
