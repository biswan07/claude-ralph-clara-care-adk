"""Unit tests for support contacts population in claim_status tool."""

import json
from unittest.mock import MagicMock, patch
import pytest
from clara_care.tools.claim_status import update_claim_status

class MockToolContext:
    """Mock ToolContext for testing."""
    def __init__(self, state_dict=None):
        self.state = state_dict or {}

@pytest.fixture
def mock_supabase_client():
    with patch("clara_care.tools.claim_status.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

def test_update_claim_status_web_search_format_insert(mock_supabase_client):
    """Test insertion with web_search_result format."""
    # Mock update response
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "claim-123"}]
    
    # Mock deduplication check (no existing record)
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    contact_details = {
        "brand_searched": "Sony",
        "emails": [
            {
                "email": "support@sony.com",
                "validation_score": 0.95,
                "source_url": "https://sony.com/support",
                "phone": "1-800-SONY"
            },
            {
                "email": "bad@sony.com",
                "validation_score": 0.1
            }
        ],
        "sources": ["https://sony.com/support"]
    }

    update_claim_status(
        claim_id="claim-123",
        status="submitted",
        contact_details=contact_details
    )

    # Verify insert called with correct data
    # We expect the email with highest score (0.95)
    expected_data = {
        "brand_name": "Sony",
        "support_email": "support@sony.com",
        "support_url": "https://sony.com/support",
        "confidence_score": 0.95,
        "source": "web_search",
        "support_phone": "1-800-SONY"
    }
    
    # Verify insert was called
    # Note: We need to find the insert call. 
    # The client.table("support_contacts").insert(...) call
    
    # Filter calls to table("support_contacts")
    support_contacts_calls = [c for c in mock_supabase_client.table.call_args_list if c[0][0] == "support_contacts"]
    assert len(support_contacts_calls) >= 1
    
    # Get the mock object returned by table("support_contacts")
    # This is tricky because table() is called multiple times.
    # But usually checks are done on the chain.
    
    # Let's check the insert call on the return value of table("support_contacts")
    # Since we can't easily distinguish which call returned which mock if they are same, 
    # we assume the chained calls are recorded.
    
    # However, simplistic check: verify insert was called with expected data
    # The chain is client.table().insert()
    
    # We can inspect verify the insert call arguments
    # We have to be careful because table() is also called for claim_status_history
    
    # A better way is to check if any insert call matched
    found_insert = False
    for call in mock_supabase_client.table.return_value.insert.call_args_list:
        args, _ = call
        if args[0] == expected_data:
            found_insert = True
            break
            
    assert found_insert, "Expected insert data not found in calls"


def test_update_claim_status_flat_format_insert(mock_supabase_client):
    """Test insertion with flat format (backward compatibility)."""
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "claim-123"}]
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    contact_details = {
        "brand_name": "Samsung",
        "support_email": "support@samsung.com",
        "support_phone": "1-800-SAMSUNG",
        "support_url": "https://samsung.com",
        "confidence_score": 0.9,
        "source": "internal_db",
        "product_category": "Electronics"
    }

    update_claim_status(
        claim_id="claim-123",
        status="submitted",
        contact_details=contact_details
    )

    expected_data = {
        "brand_name": "Samsung",
        "support_email": "support@samsung.com",
        "support_phone": "1-800-SAMSUNG",
        "support_url": "https://samsung.com",
        "confidence_score": 0.9,
        "source": "internal_db",
        "product_category": "Electronics"
    }
    
    found_insert = False
    for call in mock_supabase_client.table.return_value.insert.call_args_list:
        args, _ = call
        if args[0] == expected_data:
            found_insert = True
            break
    assert found_insert


def test_update_claim_status_deduplication(mock_supabase_client):
    """Test that existing records block insertion."""
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "claim-123"}]
    
    # Mock deduplication check (EXISTING record)
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "existing-contact-id"}]

    contact_details = {
        "brand_searched": "Sony",
        "emails": [{"email": "support@sony.com", "validation_score": 0.95}]
    }

    with patch("clara_care.tools.claim_status.logger") as mock_logger:
        update_claim_status(
            claim_id="claim-123",
            status="submitted",
            contact_details=contact_details
        )
        
        # Verify info log about skipping
        mock_logger.info.assert_any_call("Support contact for 'Sony' already exists. Skipping insert.")
        
        # Verify NO insert call for this brand
        # This is harder to check strictly without strict mock ordering, but we can check calls
        
        # Ensure insert was NOT called with Sony data
        for call in mock_supabase_client.table.return_value.insert.call_args_list:
            args, _ = call
            # We assume claim_status_history insert happens, but support_contacts should not
            data = args[0]
            if isinstance(data, dict) and data.get("brand_name") == "Sony":
                pytest.fail("Insert called for Sony despite existing record")


def test_update_claim_status_no_emails_found(mock_supabase_client):
    """Test that nothing breaks if no emails found in web search result."""
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "claim-123"}]
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    contact_details = {
        "brand_searched": "Unknown",
        "emails": [], # Empty list
        "sources": []
    }
    
    update_claim_status(
        claim_id="claim-123",
        status="requires_review",
        contact_details=contact_details
    )
    
    # Should complete without error and NOT insert support contact
    for call in mock_supabase_client.table.return_value.insert.call_args_list:
        args, _ = call
        data = args[0]
        if isinstance(data, dict) and data.get("brand_name") == "Unknown":
            pytest.fail("Insert called for Unknown brand with no email data")
