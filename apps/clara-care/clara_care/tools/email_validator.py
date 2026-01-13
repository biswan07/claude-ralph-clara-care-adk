"""Email validation tool for assessing email address legitimacy.

This tool performs comprehensive validation of email addresses including
format validation, DNS MX record lookup, brand domain matching, and
suspicious pattern detection.
"""

from __future__ import annotations

import json
import logging
import re
import socket
from typing import Any

logger = logging.getLogger(__name__)

# Email validation regex pattern (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    re.IGNORECASE,
)

# Free email providers that may indicate non-official support addresses
FREE_EMAIL_PROVIDERS = frozenset({
    "gmail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "aol.com",
    "icloud.com",
    "mail.com",
    "protonmail.com",
    "proton.me",
    "zoho.com",
    "yandex.com",
    "gmx.com",
    "gmx.net",
    "tutanota.com",
    "fastmail.com",
})

# Suspicious TLDs that may indicate fake domains
SUSPICIOUS_TLDS = frozenset({
    "xyz",
    "top",
    "click",
    "link",
    "info",
    "biz",
    "win",
    "loan",
    "work",
    "date",
    "racing",
    "review",
    "download",
    "stream",
})


def check_email_format(email: str) -> tuple[bool, list[str]]:
    """Check if email has valid RFC 5322 format.

    Args:
        email: Email address to validate.

    Returns:
        Tuple of (is_valid, list of validation issues).
    """
    issues: list[str] = []

    if not email:
        return False, ["Email is empty"]

    email = email.strip()

    # Check basic format with regex
    if not EMAIL_PATTERN.match(email):
        issues.append("Email format does not match RFC 5322 pattern")
        return False, issues

    # Split email into local and domain parts
    if "@" not in email:
        issues.append("Email missing @ symbol")
        return False, issues

    local_part, domain = email.rsplit("@", 1)

    # Local part validation
    if len(local_part) < 1:
        issues.append("Local part (before @) is empty")
    elif len(local_part) > 64:
        issues.append("Local part exceeds 64 characters")
    if local_part.startswith("."):
        issues.append("Local part starts with period")
    if local_part.endswith("."):
        issues.append("Local part ends with period")
    if ".." in local_part:
        issues.append("Local part contains consecutive periods")

    # Domain validation
    if len(domain) < 3:
        issues.append("Domain is too short")
    elif len(domain) > 255:
        issues.append("Domain exceeds 255 characters")
    if domain.startswith("."):
        issues.append("Domain starts with period")
    if domain.startswith("-"):
        issues.append("Domain starts with hyphen")
    if domain.endswith("-"):
        issues.append("Domain ends with hyphen")
    if ".." in domain:
        issues.append("Domain contains consecutive periods")

    return len(issues) == 0, issues


def check_domain_mx_records(domain: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Check if domain has valid MX records via DNS lookup.

    Args:
        domain: Domain name to check.
        timeout: DNS query timeout in seconds.

    Returns:
        Tuple of (has_mx_records, message).
    """
    original_timeout = socket.getdefaulttimeout()
    try:
        # Set socket timeout for DNS queries
        socket.setdefaulttimeout(timeout)

        try:
            # Try to get MX records using dnspython
            import dns.resolver  # type: ignore[import-not-found]

            try:
                mx_records = dns.resolver.resolve(domain, "MX")
                if mx_records:
                    return True, f"Found {len(mx_records)} MX record(s)"
                return False, "No MX records found"
            except dns.resolver.NoAnswer:
                # No MX records, but domain might still accept email via A record
                try:
                    a_records = dns.resolver.resolve(domain, "A")
                    if a_records:
                        return True, "No MX records but A record exists"
                except Exception:
                    pass
                return False, "No MX or A records found"
            except dns.resolver.NXDOMAIN:
                return False, "Domain does not exist (NXDOMAIN)"
            except dns.resolver.NoNameservers:
                return False, "No nameservers available for domain"
            except Exception as e:
                return False, f"DNS lookup error: {e!s}"

        except ImportError:
            # dnspython not available, use socket-based fallback
            try:
                socket.gethostbyname(domain)
                return True, "Domain resolves (MX check unavailable)"
            except socket.gaierror:
                return False, "Domain does not resolve"

    except Exception as e:
        logger.warning("MX record check failed for %s: %s", domain, e)
        return False, f"MX check error: {e!s}"

    finally:
        socket.setdefaulttimeout(original_timeout)


def check_domain_matches_brand(
    email: str,
    brand_name: str,
) -> tuple[bool, float, str]:
    """Check if email domain matches the expected brand.

    Args:
        email: Email address to check.
        brand_name: Expected brand name (e.g., "Sony", "Apple").

    Returns:
        Tuple of (matches, confidence_score, reasoning).
    """
    if "@" not in email or not brand_name:
        return False, 0.0, "Invalid email or brand name"

    domain = email.rsplit("@", 1)[1].lower()
    brand_lower = brand_name.lower().strip()
    domain_without_tld = domain.rsplit(".", 1)[0] if "." in domain else domain

    # Direct match: brand.com, brand.co.uk, etc.
    if brand_lower == domain_without_tld:
        return True, 1.0, f"Domain '{domain}' exactly matches brand '{brand_name}'"

    # Brand contained in domain: support.brand.com, brand-support.com
    if brand_lower in domain.replace("-", "").replace(".", ""):
        return True, 0.9, f"Domain '{domain}' contains brand '{brand_name}'"

    # Check for common brand domain patterns
    brand_variations = [
        brand_lower,
        brand_lower.replace(" ", ""),
        brand_lower.replace(" ", "-"),
        brand_lower.replace(".", ""),
    ]

    for variation in brand_variations:
        if variation in domain_without_tld:
            return True, 0.8, f"Domain contains brand variation '{variation}'"

    no_match_msg = f"Domain '{domain}' does not appear to match brand '{brand_name}'"
    return False, 0.0, no_match_msg


def detect_suspicious_patterns(email: str) -> tuple[list[str], float]:
    """Detect suspicious patterns in email address.

    Args:
        email: Email address to analyze.

    Returns:
        Tuple of (list of suspicion flags, penalty score 0.0-1.0).
    """
    flags: list[str] = []
    penalty = 0.0

    if "@" not in email:
        return ["Invalid email format"], 1.0

    local_part, domain = email.rsplit("@", 1)
    local_lower = local_part.lower()
    domain_lower = domain.lower()

    # Check for free email provider
    if domain_lower in FREE_EMAIL_PROVIDERS:
        flags.append(f"Free email provider: {domain_lower}")
        penalty += 0.4

    # Check for suspicious TLD
    tld = domain_lower.rsplit(".", 1)[-1] if "." in domain_lower else ""
    if tld in SUSPICIOUS_TLDS:
        flags.append(f"Suspicious TLD: .{tld}")
        penalty += 0.3

    # Check for excessive numbers in domain
    domain_no_tld = domain_lower.rsplit(".", 1)[0] if "." in domain_lower else domain
    digit_count = sum(1 for c in domain_no_tld if c.isdigit())
    if digit_count > 3:
        flags.append(f"Domain contains many numbers: {digit_count} digits")
        penalty += 0.2

    # Check for random-looking domain (high consonant ratio)
    letters = [c for c in domain_no_tld.replace("-", "") if c.isalpha()]
    if len(letters) > 4:
        vowels = sum(1 for c in letters if c in "aeiou")
        vowel_ratio = vowels / len(letters)
        if vowel_ratio < 0.15:
            flags.append("Domain appears random (low vowel ratio)")
            penalty += 0.15

    # Check for suspicious local part patterns
    if local_lower.startswith("no-reply") or local_lower.startswith("noreply"):
        flags.append("No-reply address unlikely to be support contact")
        penalty += 0.1

    if local_lower.startswith("admin") or local_lower.startswith("postmaster"):
        flags.append("Administrative address unlikely to be support contact")
        penalty += 0.05

    # Check for very long email addresses
    if len(email) > 100:
        flags.append(f"Unusually long email address: {len(email)} characters")
        penalty += 0.1

    # Check for IP address in domain (e.g., user@192.168.1.1)
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if ip_pattern.match(domain):
        flags.append("Domain is an IP address")
        penalty += 0.5

    # Cap penalty at 1.0
    return flags, min(penalty, 1.0)


def calculate_validation_score(
    format_valid: bool,
    domain_exists: bool,
    domain_matches_brand: bool,
    brand_match_confidence: float,
    suspicion_penalty: float,
) -> float:
    """Calculate overall validation score for an email.

    Args:
        format_valid: Whether email format is valid.
        domain_exists: Whether domain has valid MX records.
        domain_matches_brand: Whether domain matches expected brand.
        brand_match_confidence: Confidence score for brand match (0.0-1.0).
        suspicion_penalty: Penalty from suspicious patterns (0.0-1.0).

    Returns:
        Validation score between 0.0 and 1.0.
    """
    if not format_valid:
        return 0.0

    # Start with base score
    score = 0.5

    # Add points for domain existence
    if domain_exists:
        score += 0.2

    # Add points for brand match
    if domain_matches_brand:
        score += 0.3 * brand_match_confidence

    # Apply suspicion penalty
    score = score * (1.0 - suspicion_penalty)

    # Ensure score is within bounds
    return max(0.0, min(1.0, score))


def validate_email(
    email: str,
    brand_name: str = "",
    check_mx: bool = True,
    tool_context: Any = None,
) -> str:
    """
    Validate an email address for legitimacy.

    This tool performs comprehensive validation of email addresses to help
    assess whether they are legitimate manufacturer support contacts. It checks
    format validity, DNS MX records, brand domain matching, and suspicious
    patterns.

    Args:
        email (str): The email address to validate.
        brand_name (str): Expected brand name to check domain match
            (e.g., "Sony", "Apple"). Leave empty to skip brand matching.
        check_mx (bool): Whether to check DNS MX records. Set to False
            to skip DNS lookups (faster but less thorough).
        tool_context (ToolContext): ADK context for state access (ALWAYS LAST).

    Returns:
        JSON string with validation results containing:
        - is_valid (bool): Overall validity assessment
        - format_valid (bool): Whether email format is RFC 5322 compliant
        - format_issues (list): Any format validation issues found
        - domain_exists (bool): Whether domain has valid MX records
        - domain_check_message (str): Details about MX record check
        - domain_matches_brand (bool): Whether domain matches expected brand
        - brand_match_confidence (float): Confidence in brand match (0.0-1.0)
        - brand_match_reasoning (str): Explanation of brand match assessment
        - suspicion_flags (list): List of suspicious patterns detected
        - suspicion_penalty (float): Penalty score from suspicions (0.0-1.0)
        - validation_score (float): Overall validation score (0.0-1.0)
        - message (str): Human-readable summary

    Example:
        Input: email="support@sony.com", brand_name="Sony"
        Output: {"is_valid": true, "validation_score": 0.95,
                 "domain_matches_brand": true, ...}
    """
    # Validate input
    if not email or not email.strip():
        return json.dumps({
            "is_valid": False,
            "format_valid": False,
            "format_issues": ["Email is empty or missing"],
            "domain_exists": False,
            "domain_check_message": "Skipped - invalid email",
            "domain_matches_brand": False,
            "brand_match_confidence": 0.0,
            "brand_match_reasoning": "Skipped - invalid email",
            "suspicion_flags": [],
            "suspicion_penalty": 0.0,
            "validation_score": 0.0,
            "message": "Error: email is required and cannot be empty.",
        })

    email_clean = email.strip().lower()

    # Get user_id from session state if available (for logging)
    user_id: str | None = None
    if tool_context is not None:
        state = getattr(tool_context, "state", None)
        if state is not None:
            user_id_value = state.get("user_id")
            if isinstance(user_id_value, str):
                user_id = user_id_value

    logger.info(
        "Validating email: %s, brand=%s, user_id=%s",
        email_clean,
        brand_name,
        user_id,
    )

    # Step 1: Check email format
    format_valid, format_issues = check_email_format(email_clean)

    # Step 2: Check MX records (if format is valid and check_mx is enabled)
    domain_exists = False
    domain_check_message = "Skipped"
    if format_valid and check_mx:
        domain = email_clean.rsplit("@", 1)[1]
        domain_exists, domain_check_message = check_domain_mx_records(domain)
    elif format_valid:
        domain_check_message = "Skipped - MX check disabled"

    # Step 3: Check brand match (if brand_name provided)
    domain_matches_brand = False
    brand_match_confidence = 0.0
    brand_match_reasoning = "Skipped - no brand name provided"
    if brand_name and brand_name.strip() and format_valid:
        domain_matches_brand, brand_match_confidence, brand_match_reasoning = (
            check_domain_matches_brand(email_clean, brand_name)
        )

    # Step 4: Detect suspicious patterns
    suspicion_flags, suspicion_penalty = detect_suspicious_patterns(email_clean)

    # Step 5: Calculate overall validation score
    validation_score = calculate_validation_score(
        format_valid=format_valid,
        domain_exists=domain_exists,
        domain_matches_brand=domain_matches_brand,
        brand_match_confidence=brand_match_confidence,
        suspicion_penalty=suspicion_penalty,
    )

    # Determine overall validity (format valid + reasonable score)
    is_valid = format_valid and validation_score >= 0.3

    # Build human-readable message
    if not format_valid:
        message = f"Invalid email format: {', '.join(format_issues)}"
    elif validation_score >= 0.7:
        message = f"Email appears legitimate (score: {validation_score:.2f})"
    elif validation_score >= 0.4:
        message = f"Email may be valid but has concerns (score: {validation_score:.2f})"
    else:
        message = f"Email has significant concerns (score: {validation_score:.2f})"

    if suspicion_flags:
        message += f". Concerns: {', '.join(suspicion_flags[:3])}"

    logger.info(
        "Email validation result: %s, score=%.2f, valid=%s",
        email_clean,
        validation_score,
        is_valid,
    )

    return json.dumps({
        "is_valid": is_valid,
        "format_valid": format_valid,
        "format_issues": format_issues,
        "domain_exists": domain_exists,
        "domain_check_message": domain_check_message,
        "domain_matches_brand": domain_matches_brand,
        "brand_match_confidence": brand_match_confidence,
        "brand_match_reasoning": brand_match_reasoning,
        "suspicion_flags": suspicion_flags,
        "suspicion_penalty": suspicion_penalty,
        "validation_score": validation_score,
        "message": message,
    }, indent=2)
