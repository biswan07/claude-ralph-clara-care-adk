"""Internal database search tool for support contacts.

This tool searches the internal support contacts database for manufacturer
warranty support email addresses, phone numbers, and URLs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from clara_care.supabase_client import SupabaseConnectionError, get_client

logger = logging.getLogger(__name__)


def search_support_contacts(
    brand_name: str,
    product_category: str = "",
    tool_context: Any = None,
) -> str:
    """
    Search the internal support contacts database for manufacturer support information.

    Use this tool to find known warranty support contacts for a brand or product.
    The internal database contains verified support email addresses, phone numbers,
    and URLs for common manufacturers.

    Args:
        brand_name (str): The manufacturer or brand name to search for
            (e.g., "Sony", "Apple", "Samsung"). Case-insensitive partial
            matching is used.
        product_category (str): Optional product category to narrow search
            (e.g., "Electronics", "Appliances"). Leave empty to search
            across all categories.
        tool_context (ToolContext): ADK context for user_id access
            (ALWAYS LAST).

    Returns:
        JSON string with search results containing:
        - found (bool): Whether any matching contacts were found
        - results (list): List of matching support contacts with:
            - brand_name: The brand/manufacturer name
            - support_email: Primary support email address
            - support_phone: Support phone number (if available)
            - support_url: Support website URL (if available)
            - confidence_score: Confidence in the contact accuracy (0.0-1.0)
            - source: Where this contact was sourced from
        - message (str): Human-readable summary of results

    Example:
        Input: brand_name="Sony", product_category="Electronics"
        Output: {"found": true, "results": [...],
                "message": "Found 1 support contact for Sony"}
    """
    # Validate input
    if not brand_name or not brand_name.strip():
        return json.dumps({
            "found": False,
            "results": [],
            "message": "Error: brand_name is required and cannot be empty.",
        })

    # Get user_id from session state if available (for audit purposes)
    user_id: str | None = None
    if tool_context is not None:
        # ToolContext has a state dict-like attribute
        state = getattr(tool_context, "state", None)
        if state is not None:
            user_id_value = state.get("user_id")
            if isinstance(user_id_value, str):
                user_id = user_id_value

    logger.info(
        "Searching support contacts for brand=%s, category=%s, user_id=%s",
        brand_name,
        product_category or "all",
        user_id,
    )

    try:
        client = get_client()

        # Build query with case-insensitive partial match on brand_name
        query = client.table("support_contacts").select(
            "brand_name, support_email, support_phone, support_url, "
            "confidence_score, source, product_category"
        ).ilike("brand_name", f"%{brand_name.strip()}%")

        # Add category filter if provided
        if product_category and product_category.strip():
            query = query.ilike("product_category", f"%{product_category.strip()}%")

        # Execute query
        response = query.execute()

        if response.data and len(response.data) > 0:
            # Format results
            results: list[dict[str, Any]] = []
            for row in response.data:
                # Each row is a dict-like object from Supabase
                if isinstance(row, dict):
                    results.append({
                        "brand_name": row.get("brand_name"),
                        "support_email": row.get("support_email"),
                        "support_phone": row.get("support_phone"),
                        "support_url": row.get("support_url"),
                        "confidence_score": row.get("confidence_score", 0.0),
                        "source": row.get("source", "internal_db"),
                    })

            message = f"Found {len(results)} support contact(s) for '{brand_name}'"
            if product_category:
                message += f" in category '{product_category}'"

            logger.info(message)

            return json.dumps({
                "found": True,
                "results": results,
                "message": message,
            }, indent=2)
        else:
            message = f"No support contacts found for brand '{brand_name}'"
            if product_category:
                message += f" in category '{product_category}'"

            logger.info(message)

            return json.dumps({
                "found": False,
                "results": [],
                "message": message,
            })

    except SupabaseConnectionError as e:
        error_msg = f"Database connection error: {e}"
        logger.error(error_msg)
        return json.dumps({
            "found": False,
            "results": [],
            "message": error_msg,
            "error": True,
        })

    except Exception as e:
        error_msg = f"Error searching support contacts: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "found": False,
            "results": [],
            "message": error_msg,
            "error": True,
        })
