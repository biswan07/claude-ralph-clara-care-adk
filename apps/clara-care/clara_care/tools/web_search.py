"""Web search tool for finding manufacturer support contacts.

This tool uses Google Search (via ADK) to find warranty support email
addresses for manufacturers not in the internal database.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Email validation regex pattern (RFC 5322 simplified)
# Matches most valid email addresses while rejecting obviously invalid ones
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)


def extract_emails_from_text(text: str) -> list[str]:
    """Extract email addresses from text using regex.

    Args:
        text: Text to search for email addresses.

    Returns:
        List of unique email addresses found (lowercase, deduplicated).
    """
    if not text:
        return []

    matches = EMAIL_PATTERN.findall(text)
    # Deduplicate and lowercase
    seen: set[str] = set()
    unique_emails: list[str] = []
    for email in matches:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            unique_emails.append(email_lower)

    return unique_emails


def validate_email_format(email: str) -> bool:
    """Validate that an email address has valid format.

    Args:
        email: Email address to validate.

    Returns:
        True if email format is valid, False otherwise.
    """
    if not email:
        return False

    # Check basic format with regex
    if not EMAIL_PATTERN.fullmatch(email):
        return False

    # Additional checks
    local_part, domain = email.rsplit("@", 1)

    # Local part checks
    if len(local_part) < 1 or len(local_part) > 64:
        return False
    if local_part.startswith(".") or local_part.endswith("."):
        return False
    if ".." in local_part:
        return False

    # Domain checks
    if len(domain) < 3 or len(domain) > 255:
        return False
    if domain.startswith(".") or domain.startswith("-"):
        return False
    if domain.endswith("-"):
        return False

    return True


def search_support_email(
    brand_name: str,
    product_type: str = "",
    tool_context: Any = None,
) -> str:
    """
    Search the web for manufacturer warranty support contact emails.

    Use this tool when the internal database doesn't have support contact
    information for a brand. This will search Google for warranty support
    emails and return any found addresses along with source URLs.

    Args:
        brand_name (str): The manufacturer or brand name to search for
            (e.g., "Sony", "Apple", "Samsung").
        product_type (str): Optional product type to refine search
            (e.g., "TV", "laptop", "refrigerator"). Leave empty for
            general warranty support.
        tool_context (ToolContext): ADK context for state access (ALWAYS LAST).

    Returns:
        JSON string with search results containing:
        - found (bool): Whether any email addresses were found
        - emails (list): List of found emails with validation status:
            - email: The email address
            - valid_format: Whether it passes format validation
            - source_url: Where the email was found (if available)
        - search_query (str): The query that was used
        - raw_results (str): Summary of search results
        - message (str): Human-readable summary

    Example:
        Input: brand_name="Sony", product_type="TV"
        Output: {"found": true, "emails": [{"email": "support@sony.com", ...}],
                 "search_query": "Sony TV warranty support email contact", ...}
    """
    # Validate input
    if not brand_name or not brand_name.strip():
        return json.dumps({
            "found": False,
            "emails": [],
            "search_query": "",
            "raw_results": "",
            "message": "Error: brand_name is required and cannot be empty.",
        })

    # Build targeted search query
    brand_clean = brand_name.strip()
    query_parts = [brand_clean]
    if product_type and product_type.strip():
        query_parts.append(product_type.strip())
    query_parts.extend(["warranty", "support", "email", "contact"])
    search_query = " ".join(query_parts)

    # Get user_id from session state if available (for logging)
    user_id: str | None = None
    if tool_context is not None:
        state = getattr(tool_context, "state", None)
        if state is not None:
            user_id_value = state.get("user_id")
            if isinstance(user_id_value, str):
                user_id = user_id_value

    logger.info(
        "Web search for support email: query=%s, user_id=%s",
        search_query,
        user_id,
    )

    # NOTE: This tool is designed to be used alongside the google_search built-in tool.
    # The agent should use google_search first to get search results, then pass those
    # results to this tool for email extraction. Alternatively, this function returns
    # a structured format indicating what search query should be used.
    #
    # In the actual workflow:
    # 1. Agent calls google_search with the search_query
    # 2. Agent receives search results
    # 3. Agent passes relevant text/URLs to extract emails
    #
    # For now, we return the search query that should be used and provide
    # a mechanism to extract emails from provided search results.

    # Check if search results were provided in the tool context state
    search_results: str | None = None
    source_urls: list[str] = []
    if tool_context is not None:
        state = getattr(tool_context, "state", None)
        if state is not None:
            # The agent may have stored search results in state
            search_results_value = state.get("web_search_raw_results")
            if isinstance(search_results_value, str):
                search_results = search_results_value
            source_urls_value = state.get("web_search_source_urls")
            if isinstance(source_urls_value, list):
                source_urls = [u for u in source_urls_value if isinstance(u, str)]

    if search_results:
        # Extract emails from provided search results
        found_emails = extract_emails_from_text(search_results)

        # Filter for likely support-related emails
        support_keywords = ["support", "warranty", "service", "help", "care", "contact"]
        brand_lower = brand_clean.lower()

        # Build email results with validation
        email_results: list[dict[str, Any]] = []
        for email in found_emails:
            is_valid = validate_email_format(email)
            email_lower = email.lower()

            # Check if email appears to be support-related
            is_support_related = any(kw in email_lower for kw in support_keywords)
            domain = email_lower.split("@")[1] if "@" in email_lower else ""

            # Check if domain might match brand
            domain_matches_brand = brand_lower in domain.replace(".", "")

            email_results.append({
                "email": email,
                "valid_format": is_valid,
                "is_support_related": is_support_related,
                "domain_matches_brand": domain_matches_brand,
                "source_url": source_urls[0] if source_urls else None,
            })

        if email_results:
            message = f"Found {len(email_results)} email(s) for '{brand_clean}'"
            logger.info(message)
            # Truncate raw results if too long
            truncated_results = search_results
            if len(search_results) > 500:
                truncated_results = search_results[:500] + "..."
            return json.dumps({
                "found": True,
                "emails": email_results,
                "search_query": search_query,
                "raw_results": truncated_results,
                "source_urls": source_urls,
                "message": message,
            }, indent=2)
        else:
            no_email_msg = (
                f"No email addresses found in search results for '{brand_clean}'"
            )
            logger.info(no_email_msg)
            # Truncate raw results if too long
            truncated_results = search_results
            if len(search_results) > 500:
                truncated_results = search_results[:500] + "..."
            return json.dumps({
                "found": False,
                "emails": [],
                "search_query": search_query,
                "raw_results": truncated_results,
                "source_urls": source_urls,
                "message": no_email_msg,
            }, indent=2)
    else:
        # No search results provided - return the query to use
        message = (
            f"Use google_search with query: '{search_query}'. "
            f"Then store results in state['web_search_raw_results'] and call again."
        )
        logger.info("No search results provided, returning search query")
        return json.dumps({
            "found": False,
            "emails": [],
            "search_query": search_query,
            "raw_results": "",
            "source_urls": [],
            "message": message,
            "action_required": "Execute google_search with the provided query",
        }, indent=2)


def parse_search_results_for_emails(
    search_results: str,
    brand_name: str = "",
    tool_context: Any = None,
) -> str:
    """
    Parse search results text and extract email addresses.

    Use this tool after running google_search to extract and validate
    email addresses from the search results. This separates the search
    execution from the parsing logic.

    Args:
        search_results (str): Raw text from google_search results to parse.
        brand_name (str): Brand name to check domain matching (optional).
        tool_context (ToolContext): ADK context for state access (ALWAYS LAST).

    Returns:
        JSON string with extracted emails containing:
        - found (bool): Whether any email addresses were found
        - emails (list): List of found emails with validation:
            - email: The email address
            - valid_format: Whether format is valid
            - is_support_related: Whether it appears to be support email
            - domain_matches_brand: Whether domain matches brand name
        - count (int): Number of emails found
        - message (str): Human-readable summary
    """
    if not search_results or not search_results.strip():
        return json.dumps({
            "found": False,
            "emails": [],
            "count": 0,
            "message": "Error: search_results is required and cannot be empty.",
        })

    # Extract emails
    found_emails = extract_emails_from_text(search_results)

    if not found_emails:
        return json.dumps({
            "found": False,
            "emails": [],
            "count": 0,
            "message": "No email addresses found in the provided search results.",
        })

    # Support-related keywords
    support_keywords = ["support", "warranty", "service", "help", "care", "contact"]
    brand_lower = brand_name.lower().strip() if brand_name else ""

    # Build results with validation
    email_results: list[dict[str, Any]] = []
    for email in found_emails:
        is_valid = validate_email_format(email)
        email_lower = email.lower()

        # Check if email appears to be support-related
        is_support_related = any(kw in email_lower for kw in support_keywords)

        # Check if domain might match brand
        domain = email_lower.split("@")[1] if "@" in email_lower else ""
        domain_no_dots = domain.replace(".", "")
        domain_matches = brand_lower in domain_no_dots if brand_lower else False

        email_results.append({
            "email": email,
            "valid_format": is_valid,
            "is_support_related": is_support_related,
            "domain_matches_brand": domain_matches,
        })

    message = f"Found {len(email_results)} email address(es) in search results"
    logger.info(message)

    return json.dumps({
        "found": True,
        "emails": email_results,
        "count": len(email_results),
        "message": message,
    }, indent=2)
