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
    """Enum for warranty claim status."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"  # Waiting for human review
    SUBMITTED = "submitted"  # Successfully submitted to manufacturer
    FAILED = "failed"  # Submission failed
    REQUIRES_REVIEW = "requires_review"  # Needs manual intervention


def update_claim_status(
    claim_id: str,
    status: str,
    support_email_used: str = "",
    confidence_score: float = 0.0,
    judge_reasoning: str = "",
    attempted_emails: str = "",
    pending_reason: str = "",
    actions_taken: list[str] | None = None,
    email_body: str = "",
    contact_details: dict[str, Any] | None = None,
    email_html_body: str = "",
    receipt_image_url: str = "",
    tool_context: Any = None,
) -> str:
    """
    Update the status of a warranty claim.

    Use this tool to update claim status as it progresses through the workflow.
    The tool maintains an audit trail by recording status history.

    Args:
        claim_id (str): The unique identifier for the warranty claim.
        status (str): New status. Must be one of: pending, submitted, failed,
            requires_review.
        support_email_used (str): The support email address used for submission
            (if applicable). Use for submitted status.
        confidence_score (float): Confidence score from the judge agent (0.0-1.0).
        judge_reasoning (str): Explanation from the judge agent for the decision.
        attempted_emails (str): JSON array of attempted email addresses with their
            confidence scores. Use for pending status (low confidence flow).
            Format: '[{"email": "support@brand.com", "score": 0.65}]'
        pending_reason (str): Human-readable reason for pending status.
            Example: "Low confidence - requires human verification"
        actions_taken (list[str]): List of actions performed (sent in webhook response).
        email_body (str): Full text of the sent email (sent in webhook response).
        contact_details (dict): Support contact details found via web search to
            insert into support_contacts table. Should contain: brand_name,
            support_email, support_phone, support_url, etc.
        email_html_body (str): Full HTML of the composed email (for manual review).
        receipt_image_url (str): URL of the receipt image (for manual review).
        tool_context (ToolContext): ADK context for user_id access (ALWAYS LAST).

    Returns:
        JSON string with update result containing:
        - success (bool): Whether the update was successful
        - claim_id (str): The claim ID that was updated
        - status (str): The new status value
        - updated_at (str): ISO timestamp of the update
        - message (str): Human-readable result message

    Example (submitted):
        Input: claim_id="claim-123", status="submitted", confidence_score=0.85,
               support_email_used="support@sony.com"
        Output: {"success": true, "claim_id": "claim-123", "status": "submitted",
                "updated_at": "2026-01-13T10:30:00Z", "message": "Claim status updated"}

    Example (verified pending):
        Input: claim_id="claim-123", status="pending", confidence_score=0.65,
               attempted_emails='[{"email": "help@brand.com", "score": 0.65}]',
               pending_reason="Low confidence - requires human verification"
        Output: {"success": true, "claim_id": "claim-123", "status": "pending", ...}
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
        # Normalize to lowercase to match Enum values
        status_lower = status.strip().lower()
        validated_status = ClaimStatus(status_lower)
    except ValueError:
        valid_statuses = [s.value for s in ClaimStatus]
        return json.dumps({
            "success": False,
            "claim_id": claim_id.strip(),
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

        # If status is pending or requires_review (manual review needed), 
        # insert into manual_review_requests table
        if validated_status.value in [ClaimStatus.PENDING.value, ClaimStatus.REQUIRES_REVIEW.value]:
            if email_html_body or email_body:
                try:
                    review_data = {
                        "claim_id": claim_id.strip(),
                        "receipt_image_url": receipt_image_url,
                        "email_body_text": email_body,
                        "email_body_html": email_html_body,
                        "support_email": support_email_used,
                        "confidence_score": confidence_score,
                        "status": "pending"
                    }
                    client.table("manual_review_requests").insert(review_data).execute()
                    logger.info(f"Created manual review request for claim {claim_id}")
                except Exception as mr_error:
                    logger.warning(f"Failed to create manual review request: {mr_error}")
                    # Continue with main update logic even if this fails

        # Only include optional fields if they have values
        if support_email_used and support_email_used.strip():
            update_data["support_email_used"] = support_email_used.strip()

        if confidence_score > 0:
            update_data["confidence_score"] = confidence_score

        if judge_reasoning and judge_reasoning.strip():
            update_data["judge_reasoning"] = judge_reasoning.strip()

        # For PENDING status (low-confidence flow), store attempted emails
        if attempted_emails and attempted_emails.strip():
            update_data["attempted_emails"] = attempted_emails.strip()

        # Store pending reason for human review context
        if pending_reason and pending_reason.strip():
            update_data["pending_reason"] = pending_reason.strip()

        # Construct webhook_response as formatted text per user request
        if actions_taken or email_body:
            parts = []
            if actions_taken:
                parts.append(", ".join(actions_taken))
            if email_body:
                parts.append(email_body)
            
            update_data["webhook_response"] = "\n\n".join(parts)

        response = client.table("warranty_claims").update(
            update_data
        ).eq("claim_id", claim_id.strip()).execute()

        # Insert into support_contacts if contact_details provided (from web search)
        if contact_details and isinstance(contact_details, dict):
            # Basic validation - brand_name is required by schema
            # Logic to handle both flat structure (db_search) and nested (web_search)
            
            brand_name = contact_details.get("brand_name")
            insert_data = {}
            
            # CASE 1: Web Search Result Structure
            # Format: { "brand_searched": "Sony", "emails": [...], "sources": [...] }
            if "brand_searched" in contact_details:
                brand_name = contact_details.get("brand_searched")
                
                # Find best email (highest validation score)
                emails = contact_details.get("emails", [])
                best_email_obj = None
                highest_score = -1.0
                
                for email_obj in emails:
                    score = email_obj.get("validation_score", 0.0)
                    if score > highest_score:
                        highest_score = score
                        best_email_obj = email_obj
                
                if best_email_obj:
                    insert_data = {
                        "brand_name": brand_name,
                        "support_email": best_email_obj.get("email"),
                        "support_url": best_email_obj.get("source_url"),
                        "confidence_score": best_email_obj.get("validation_score", 0.0),
                        "source": "web_search",
                        # validation_score is already float usually, ensure it
                    }
                    
                    # Try to get phone if available in raw result (unlikely in this flow but safe)
                    if "phone" in best_email_obj:
                        insert_data["support_phone"] = best_email_obj.get("phone")
                    
            # CASE 2: Flat Structure (likely from db_search or direct tool usage)
            # Format: { "brand_name": "Sony", "support_email": "...", ... }
            elif "brand_name" in contact_details:
                brand_name = contact_details.get("brand_name")
                insert_data = {
                    "brand_name": brand_name,
                    "support_email": contact_details.get("support_email"),
                    "support_phone": contact_details.get("support_phone"),
                    "support_url": contact_details.get("support_url"),
                    "confidence_score": contact_details.get("confidence_score", 0.0),
                    "source": contact_details.get("source", "web_search"), # Default to web_search if not specified
                    "product_category": contact_details.get("product_category"),
                }

            if brand_name and insert_data:
                try:
                    # DEDUPLICATION: Check if brand already exists
                    # We only want to populate if we don't have it.
                    # Or maybe we update if confidence is higher? 
                    # Requirement says "insert ... if not existingly available"
                    
                    # Clean insert_data to remove None values
                    insert_data = {k: v for k, v in insert_data.items() if v is not None}

                    existing = client.table("support_contacts").select(
                        "id, support_email, support_phone, support_url"
                    ).eq("brand_name", brand_name).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        existing_record = existing.data[0]
                        updated_fields = {}
                        
                        # Check for missing fields in DB that we have new data for
                        if not existing_record.get("support_email") and insert_data.get("support_email"):
                            updated_fields["support_email"] = insert_data["support_email"]
                            
                        if not existing_record.get("support_phone") and insert_data.get("support_phone"):
                            updated_fields["support_phone"] = insert_data["support_phone"]
                            
                        if not existing_record.get("support_url") and insert_data.get("support_url"):
                            updated_fields["support_url"] = insert_data["support_url"]
                            
                        if updated_fields:
                            updated_fields["updated_at"] = now_iso
                            client.table("support_contacts").update(updated_fields).eq(
                                "id", existing_record["id"]
                            ).execute()
                            logger.info(
                                "Updated support contact for '%s' with new fields: %s",
                                brand_name,
                                list(updated_fields.keys())
                            )
                        else:
                            logger.info(
                                "Support contact for '%s' already exists. Skipping update.",
                                brand_name
                            )
                    else:
                        client.table("support_contacts").insert(insert_data).execute()
                        logger.info("Inserted new support contact for %s", brand_name)
                    
                except Exception as e:
                    # Don't fail the whole claim update if contact insert fails
                    logger.error(f"Failed to insert support contact: {e}")
            else:
                logger.warning("Could not extract brand_name or data for support_contacts insert.")

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
        attempted_emails_val = attempted_emails.strip() if attempted_emails else None
        pending_reason_val = pending_reason.strip() if pending_reason else None
        history_data: dict[str, Any] = {
            "claim_id": claim_id.strip(),
            "status": validated_status.value,
            "support_email_used": email_for_history,
            "confidence_score": confidence_score if confidence_score > 0 else None,
            "judge_reasoning": judge_reasoning.strip() if judge_reasoning else None,
            "attempted_emails": attempted_emails_val,
            "pending_reason": pending_reason_val,
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
            - claim_id: Claim identifier
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
            "claim_id, status, support_email_used, confidence_score, "
            "judge_reasoning, updated_at, created_at"
        ).eq("claim_id", claim_id.strip()).execute()

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
                "claim_id": claim_data.get("claim_id"),
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
        - receipt_image_url (str): URL of the receipt image
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
        # NOTE: Only selecting columns that effectively exist in the DB Schema
        response = client.table("warranty_claims").select(
            "id, claim_id, status, user_name, user_email, "
            "brand_name, product_name, "
            "model_number, warranty_period, store_name, purchase_location, "
            "issue_description, receipt_id, receipt_image_url, "
            " created_at, updated_at"
        ).eq("claim_id", claim_id.strip()).execute()

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

        # Refresh signed URL if necessary to ensure it's accessible
        receipt_image_url = claim_data.get("receipt_image_url")
        if receipt_image_url and "/storage/v1/object/sign/" in receipt_image_url:
            try:
                # Parse existing URL to get bucket and path
                base_parts = receipt_image_url.split("/storage/v1/object/sign/")
                if len(base_parts) == 2:
                    path_component = base_parts[1]
                    # Format: <bucket>/<path/to/file><?query>
                    # Separate bucket from path
                    path_parts = path_component.split("/", 1)
                    if len(path_parts) == 2:
                        bucket_name = path_parts[0]
                        file_path_full = path_parts[1]
                        
                        # Remove existing query parameters (like ?token=...)
                        file_path = file_path_full.split("?")[0]
                        
                        # Generate new signed URL (valid for 1 week = 604800 seconds)
                        # Note: storage.from_ is used because 'from' is a reserved keyword
                        res = client.storage.from_(bucket_name).create_signed_url(file_path, 604800)
                        
                        if isinstance(res, dict) and "signedURL" in res:
                            new_signed_url = res["signedURL"]
                            # Handle relative vs absolute URL
                            if new_signed_url.startswith("/"):
                                 # Prepend base URL if relative
                                receipt_image_url = f"{base_parts[0]}{new_signed_url}"
                            else:
                                receipt_image_url = new_signed_url
                                
                            logger.info(f"Refreshed signed URL for receipt: {bucket_name}/{file_path}")
                            
                            # Persist the new signed URL to the database so it's fresh for other agents/tools
                            try:
                                client.table("warranty_claims").update(
                                    {"receipt_image_url": receipt_image_url}
                                ).eq("claim_id", claim_id.strip()).execute()
                                logger.info(f"Updated database with new signed URL for claim {claim_id}")
                            except Exception as update_error:
                                logger.warning(f"Failed to update database with new signed URL: {update_error}")
            except Exception as e:
                logger.warning(f"Failed to refresh receipt signed URL: {e}")

        result = {
            "found": True,
            "claim_id": claim_data.get("claim_id"),
            "internal_id": claim_data.get("id"),
            "user": {
                "name": claim_data.get("user_name"),
                "email": claim_data.get("user_email"),
            },
            "product": {
                "brand": claim_data.get("brand_name"),
                "name": claim_data.get("product_name"),
                "category": None, # Not in DB
                "serial_number": None, # Not in DB
                "purchase_date": None, # Not in DB
                "model_number": claim_data.get("model_number"),
                "warranty_period": claim_data.get("warranty_period"),
                "store_name": claim_data.get("store_name"),
                "purchase_location": claim_data.get("purchase_location"),
            },
            "issue": {
                "description": claim_data.get("issue_description"),
                "occurrence_date": None, # Not in DB
            },
            "receipt_reference": claim_data.get("receipt_id"),
            "receipt_image_url": receipt_image_url,
            "status": claim_data.get("status"),
            "created_at": claim_data.get("created_at"),
            "updated_at": claim_data.get("updated_at"),
            "message": f"Found claim {claim_id.strip()}",
        }

        logger.info(
            "Claim details retrieved: claim_id=%s, brand=%s",
            claim_id.strip(),
            claim_data.get("brand_name"),
        )

        result_json = json.dumps(result, indent=2)

        # Save to state for downstream agents
        if tool_context is not None:
             state = getattr(tool_context, "state", None)
             if state is not None:
                  state["claim_details"] = result_json
                  logger.info("Saved claim_details to session state")

        return result_json

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
