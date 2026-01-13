"""Claim status management tool for warranty claim tracking.

This tool provides functions to update and retrieve warranty claim statuses,
maintaining an audit trail for compliance and operational visibility.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from clara_care.supabase_client import SupabaseConnectionError, get_client

logger = logging.getLogger(__name__)


class ClaimStatus(str, Enum):
    """Valid claim status values."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


def update_claim_status(
    claim_id: str,
    status: str,
    support_email_used: str = "",
    confidence_score: float = 0.0,
    judge_reasoning: str = "",
    tool_context: Any = None,
) -> str:
    """
    Update the status of a warranty claim.

    Use this tool to update claim status as it progresses through the workflow.
    The tool maintains an audit trail by recording status history.

    Args:
        claim_id (str): The unique identifier for the warranty claim.
        status (str): New status. Must be one of: PENDING, SUBMITTED, FAILED,
            REQUIRES_REVIEW.
        support_email_used (str): The support email address used for submission
            (if applicable).
        confidence_score (float): Confidence score from the judge agent (0.0-1.0).
        judge_reasoning (str): Explanation from the judge agent for the decision.
        tool_context (ToolContext): ADK context for user_id access (ALWAYS LAST).

    Returns:
        JSON string with update result containing:
        - success (bool): Whether the update was successful
        - claim_id (str): The claim ID that was updated
        - status (str): The new status value
        - updated_at (str): ISO timestamp of the update
        - message (str): Human-readable result message

    Example:
        Input: claim_id="claim-123", status="SUBMITTED", confidence_score=0.85
        Output: {"success": true, "claim_id": "claim-123", "status": "SUBMITTED",
                "updated_at": "2026-01-13T10:30:00Z", "message": "Claim status updated"}
    """
    # Validate claim_id
    if not claim_id or not claim_id.strip():
        return json.dumps({
            "success": False,
            "claim_id": "",
            "status": "",
            "message": "Error: claim_id is required and cannot be empty.",
        })

    # Validate status
    try:
        validated_status = ClaimStatus(status.upper())
    except ValueError:
        valid_statuses = [s.value for s in ClaimStatus]
        return json.dumps({
            "success": False,
            "claim_id": claim_id,
            "status": status,
            "message": f"Error: Invalid status '{status}'. Must be one of: "
            f"{', '.join(valid_statuses)}",
        })

    # Get user_id from session state if available (for audit purposes)
    user_id: str | None = None
    if tool_context is not None:
        state = getattr(tool_context, "state", None)
        if state is not None:
            user_id_value = state.get("user_id")
            if isinstance(user_id_value, str):
                user_id = user_id_value

    logger.info(
        "Updating claim status: claim_id=%s, status=%s, user_id=%s",
        claim_id.strip(),
        validated_status.value,
        user_id,
    )

    try:
        client = get_client()
        now = datetime.now(UTC)
        now_iso = now.isoformat()

        # Update claim status in warranty_claims table
        update_data: dict[str, Any] = {
            "status": validated_status.value,
            "updated_at": now_iso,
        }

        # Only include optional fields if they have values
        if support_email_used and support_email_used.strip():
            update_data["support_email_used"] = support_email_used.strip()

        if confidence_score > 0:
            update_data["confidence_score"] = confidence_score

        if judge_reasoning and judge_reasoning.strip():
            update_data["judge_reasoning"] = judge_reasoning.strip()

        response = client.table("warranty_claims").update(
            update_data
        ).eq("id", claim_id.strip()).execute()

        # Check if update was successful (at least one row affected)
        if not response.data or len(response.data) == 0:
            return json.dumps({
                "success": False,
                "claim_id": claim_id.strip(),
                "status": validated_status.value,
                "message": f"Claim with id '{claim_id}' not found.",
            })

        # Record status change in history table for audit trail
        email_for_history = support_email_used.strip() if support_email_used else None
        history_data = {
            "claim_id": claim_id.strip(),
            "status": validated_status.value,
            "support_email_used": email_for_history,
            "confidence_score": confidence_score if confidence_score > 0 else None,
            "judge_reasoning": judge_reasoning.strip() if judge_reasoning else None,
            "created_at": now_iso,
            "created_by": user_id,
        }

        client.table("claim_status_history").insert(history_data).execute()

        logger.info(
            "Claim status updated successfully: claim_id=%s, status=%s",
            claim_id.strip(),
            validated_status.value,
        )

        return json.dumps({
            "success": True,
            "claim_id": claim_id.strip(),
            "status": validated_status.value,
            "updated_at": now_iso,
            "message": f"Claim status updated to {validated_status.value}",
        }, indent=2)

    except SupabaseConnectionError as e:
        error_msg = f"Database connection error: {e}"
        logger.error(error_msg)
        return json.dumps({
            "success": False,
            "claim_id": claim_id.strip(),
            "status": "",
            "message": error_msg,
            "error": True,
        })

    except Exception as e:
        error_msg = f"Error updating claim status: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "success": False,
            "claim_id": claim_id.strip(),
            "status": "",
            "message": error_msg,
            "error": True,
        })


def get_claim_status(
    claim_id: str,
    include_history: bool = False,
    tool_context: Any = None,
) -> str:
    """
    Retrieve the current status and details of a warranty claim.

    Use this tool to check the current state of a claim, including its status,
    confidence score, and optionally the full status history.

    Args:
        claim_id (str): The unique identifier for the warranty claim.
        include_history (bool): Whether to include full status change history.
            Defaults to False.
        tool_context (ToolContext): ADK context for user_id access (ALWAYS LAST).

    Returns:
        JSON string with claim details containing:
        - found (bool): Whether the claim was found
        - claim (dict): Claim details including:
            - id: Claim identifier
            - status: Current status
            - support_email_used: Email used for submission (if any)
            - confidence_score: Judge confidence score
            - judge_reasoning: Judge decision reasoning
            - updated_at: Last update timestamp
        - history (list): Status change history (if include_history=True)
        - message (str): Human-readable summary

    Example:
        Input: claim_id="claim-123", include_history=True
        Output: {"found": true, "claim": {...}, "history": [...],
                "message": "Found claim claim-123"}
    """
    # Validate claim_id
    if not claim_id or not claim_id.strip():
        return json.dumps({
            "found": False,
            "claim": None,
            "history": [],
            "message": "Error: claim_id is required and cannot be empty.",
        })

    # Get user_id from session state if available (for audit purposes)
    user_id: str | None = None
    if tool_context is not None:
        state = getattr(tool_context, "state", None)
        if state is not None:
            user_id_value = state.get("user_id")
            if isinstance(user_id_value, str):
                user_id = user_id_value

    logger.info(
        "Retrieving claim status: claim_id=%s, include_history=%s, user_id=%s",
        claim_id.strip(),
        include_history,
        user_id,
    )

    try:
        client = get_client()

        # Query claim from warranty_claims table
        response = client.table("warranty_claims").select(
            "id, status, support_email_used, confidence_score, "
            "judge_reasoning, updated_at, created_at"
        ).eq("id", claim_id.strip()).execute()

        if not response.data or len(response.data) == 0:
            return json.dumps({
                "found": False,
                "claim": None,
                "history": [],
                "message": f"Claim with id '{claim_id}' not found.",
            })

        claim_data = response.data[0]
        if not isinstance(claim_data, dict):
            return json.dumps({
                "found": False,
                "claim": None,
                "history": [],
                "message": "Error: Unexpected data format from database.",
            })

        result: dict[str, Any] = {
            "found": True,
            "claim": {
                "id": claim_data.get("id"),
                "status": claim_data.get("status"),
                "support_email_used": claim_data.get("support_email_used"),
                "confidence_score": claim_data.get("confidence_score"),
                "judge_reasoning": claim_data.get("judge_reasoning"),
                "updated_at": claim_data.get("updated_at"),
                "created_at": claim_data.get("created_at"),
            },
            "history": [],
            "message": f"Found claim {claim_id.strip()}",
        }

        # Get status history if requested
        if include_history:
            history_response = client.table("claim_status_history").select(
                "status, support_email_used, confidence_score, "
                "judge_reasoning, created_at, created_by"
            ).eq("claim_id", claim_id.strip()).order(
                "created_at", desc=True
            ).execute()

            if history_response.data:
                history: list[dict[str, Any]] = []
                for row in history_response.data:
                    if isinstance(row, dict):
                        history.append({
                            "status": row.get("status"),
                            "support_email_used": row.get("support_email_used"),
                            "confidence_score": row.get("confidence_score"),
                            "judge_reasoning": row.get("judge_reasoning"),
                            "created_at": row.get("created_at"),
                            "created_by": row.get("created_by"),
                        })
                result["history"] = history
                result["message"] += f" with {len(history)} status change(s)"

        logger.info(
            "Claim status retrieved: claim_id=%s, status=%s",
            claim_id.strip(),
            claim_data.get("status"),
        )

        return json.dumps(result, indent=2)

    except SupabaseConnectionError as e:
        error_msg = f"Database connection error: {e}"
        logger.error(error_msg)
        return json.dumps({
            "found": False,
            "claim": None,
            "history": [],
            "message": error_msg,
            "error": True,
        })

    except Exception as e:
        error_msg = f"Error retrieving claim status: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "found": False,
            "claim": None,
            "history": [],
            "message": error_msg,
            "error": True,
        })


def get_claim_details(
    claim_id: str,
    tool_context: Any = None,
) -> str:
    """
    Retrieve full details of a warranty claim for processing.

    Use this tool to get all claim information needed for the warranty claim
    workflow, including user details, product information, and issue description.

    Args:
        claim_id (str): The unique identifier for the warranty claim.
        tool_context (ToolContext): ADK context for user_id access (ALWAYS LAST).

    Returns:
        JSON string with full claim details containing:
        - found (bool): Whether the claim was found
        - claim_id (str): The claim identifier
        - user (dict): User contact information (name, email, phone)
        - product (dict): Product details (brand, name, category, serial_number,
            purchase_date)
        - issue (dict): Issue description and occurrence date
        - receipt_reference (str): Reference to proof of purchase
        - status (str): Current claim status
        - message (str): Human-readable summary

    Example:
        Input: claim_id="CLM-12345"
        Output: {"found": true, "claim_id": "CLM-12345", "user": {...},
                "product": {...}, "issue": {...}, ...}
    """
    # Validate claim_id
    if not claim_id or not claim_id.strip():
        return json.dumps({
            "found": False,
            "claim_id": "",
            "message": "Error: claim_id is required and cannot be empty.",
        })

    # Get user_id from session state if available (for audit purposes)
    user_id: str | None = None
    if tool_context is not None:
        state = getattr(tool_context, "state", None)
        if state is not None:
            user_id_value = state.get("user_id")
            if isinstance(user_id_value, str):
                user_id = user_id_value

    logger.info(
        "Retrieving claim details: claim_id=%s, user_id=%s",
        claim_id.strip(),
        user_id,
    )

    try:
        client = get_client()

        # Query full claim details from warranty_claims table
        response = client.table("warranty_claims").select(
            "id, status, user_name, user_email, user_phone, "
            "product_brand, product_name, product_category, "
            "product_serial_number, purchase_date, "
            "issue_description, issue_occurrence_date, "
            "receipt_reference, created_at, updated_at"
        ).eq("id", claim_id.strip()).execute()

        if not response.data or len(response.data) == 0:
            return json.dumps({
                "found": False,
                "claim_id": claim_id.strip(),
                "message": f"Claim with id '{claim_id}' not found.",
            })

        claim_data = response.data[0]
        if not isinstance(claim_data, dict):
            return json.dumps({
                "found": False,
                "claim_id": claim_id.strip(),
                "message": "Error: Unexpected data format from database.",
            })

        result = {
            "found": True,
            "claim_id": claim_data.get("id"),
            "user": {
                "name": claim_data.get("user_name"),
                "email": claim_data.get("user_email"),
                "phone": claim_data.get("user_phone"),
            },
            "product": {
                "brand": claim_data.get("product_brand"),
                "name": claim_data.get("product_name"),
                "category": claim_data.get("product_category"),
                "serial_number": claim_data.get("product_serial_number"),
                "purchase_date": claim_data.get("purchase_date"),
            },
            "issue": {
                "description": claim_data.get("issue_description"),
                "occurrence_date": claim_data.get("issue_occurrence_date"),
            },
            "receipt_reference": claim_data.get("receipt_reference"),
            "status": claim_data.get("status"),
            "created_at": claim_data.get("created_at"),
            "updated_at": claim_data.get("updated_at"),
            "message": f"Found claim {claim_id.strip()}",
        }

        logger.info(
            "Claim details retrieved: claim_id=%s, brand=%s",
            claim_id.strip(),
            claim_data.get("product_brand"),
        )

        return json.dumps(result, indent=2)

    except SupabaseConnectionError as e:
        error_msg = f"Database connection error: {e}"
        logger.error(error_msg)
        return json.dumps({
            "found": False,
            "claim_id": claim_id.strip(),
            "message": error_msg,
            "error": True,
        })

    except Exception as e:
        error_msg = f"Error retrieving claim details: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "found": False,
            "claim_id": claim_id.strip(),
            "message": error_msg,
            "error": True,
        })
