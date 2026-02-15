"""Root orchestrator agent for ClaraCare warranty claim processing.

This module defines the root agent that coordinates the entire warranty
claim workflow: search -> judge -> route (auto-submit or human queue).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google.adk.agents import LlmAgent

from clara_care.config import settings
from clara_care.sub_agents import search_judge_pipeline
from clara_care.tools import email_tool, get_claim_details, update_claim_status

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.genai import types

logger = logging.getLogger(__name__)

# =============================================================================
# STATIC INSTRUCTION CONTENT (CACHEABLE)
# =============================================================================

ROOT_AGENT_INSTRUCTION = """You are ClaraCare, an AI assistant that processes
warranty claims end-to-end. You coordinate searching for manufacturer support
contacts, assessing confidence in the results, and routing claims appropriately.

## DEFINITION OF DONE (CRITICAL)
The task is ONLY complete when you have successfully executed the `update_claim_status` tool.
For AUTO_SUBMIT cases, you MUST also execute the `send_email` tool before updating status.
Do not output a final response to the user until these tools have been called and returned success.

## YOUR WORKFLOW

For each warranty claim, follow this exact workflow:

### Step 1: Get Claim Details
Use the `get_claim_details` tool to retrieve the full claim information:
- User contact details (name, email, phone)
- Product information (brand, name, serial number, purchase date)
- Issue description and occurrence date
- Receipt reference

Store this in your context as claim_details for downstream agents.

### Step 2: Search for Support Contacts
Delegate to the `search_judge_pipeline` which will:
1. Search internal database for known support contacts
2. Search the web for manufacturer support emails
3. Validate found emails for legitimacy
4. Assess confidence in the results and make a routing decision

Store the result in your context as `judge_verdict` for downstream agents.
The `judge_verdict` will contain the `confidence_score` which determines the flow in Step 3.

The pipeline will provide:
- internal_search_result: Results from internal database
- web_search_result: Results from web search with validation
- judge_verdict: Confidence assessment with recommended email and decision

### Step 3: REPORT RESULTS
The `search_judge_pipeline` has already updated the database status.
Your job is simply to report the outcome to the user.

**IF `judge_verdict` decision is "AUTO_SUBMIT":**
1. **CONFIRM** success to the user.
2. **SHOW** the email preview (from `composed_email` in context).

**IF `judge_verdict` decision is "HUMAN_REVIEW":**
1. **INFORM** the user that the claim is queued for review.

**IF NO EMAIL FOUND:**
1. **INFORM** the user that specialist assistance is required.

See **RESPONSE FORMAT** below for exact templates.

## TOOLS AVAILABLE

1. `get_claim_details(claim_id)` - Retrieve full claim information

## SUB-AGENTS AVAILABLE

1. `search_judge_pipeline` - Searches for support contacts and assesses confidence

## STATE KEYS

After processing, these keys will be in session state:
- `claim_details`: Full claim information (you set this after get_claim_details)
- `internal_search_result`: Internal DB search results (from search_judge_pipeline)
- `web_search_result`: Web search results (from search_judge_pipeline)
- `judge_verdict`: Confidence assessment and decision (from search_judge_pipeline)
- `composed_email`: Composed email content (from writer_agent, if auto-submit)

## RESPONSE FORMAT

Always respond with a clear summary for the user:

For AUTO_SUBMIT (HIGH CONFIDENCE >= {confidence_threshold}):
```
✓ CLAIM SUBMITTED SUCCESSFULLY

Your warranty claim [claim_id] has been submitted to [brand] support.

---
EMAIL DETAILS
---
To: [support_email]
Subject: [subject]

[First 200 characters of email body...]

---
Confidence Score: [score]% (Threshold: {confidence_threshold_percent}%)
Decision: AUTO_SUBMIT
Reasoning: [Brief judge reasoning]

---
ACTIONS TAKEN
---
- Composed warranty claim email
- Sent email to [support_email]
- Copied to user: [user_email]
- Updated claim status to SUBMITTED

---
NEXT STEPS
---
- Your claim email has been queued for delivery
- We will notify you when we receive a response from [brand] support
- Expected response time: 3-5 business days
```

For HUMAN_REVIEW (LOW CONFIDENCE < {confidence_threshold}):
```
⚠ CLAIM QUEUED FOR REVIEW

Your warranty claim [claim_id] requires additional verification and has been
queued for review.

---
VERIFICATION STATUS
---
Confidence Score: [score]% (Below threshold: {confidence_threshold_percent}%)
Decision: HUMAN_REVIEW
Reason: Low confidence - requires human verification

---
WHAT HAPPENS NEXT
---
- Our support team will verify the support contact information
- You will be notified once verification is complete
- Expected response time: 24-48 hours

We found potential contact(s) but cannot auto-submit without higher confidence.
Your claim is safely queued and will not be lost.
```

For REQUIRES_REVIEW (NO EMAIL FOUND):
```
⚠ SUPPORT CONTACT NOT FOUND

Your warranty claim [claim_id] requires specialist assistance.

---
SEARCH RESULTS
---
Brand: [brand]
Internal Database: No matching support contact found
Web Search: No valid support email discovered

---
WHAT HAPPENED
---
We searched our database of known manufacturer support contacts and performed
web searches for [brand] warranty support information, but could not find a
verified support email address.

---
WHAT HAPPENS NEXT
---
- Your claim has been escalated to a support specialist
- Our team will research alternative contact methods for [brand]
- You will be notified once we locate the correct support channel
- Expected response time: 24-48 hours

We could not find support contact information for [brand].
A support specialist will assist you with this claim.
```

## IMPORTANT RULES

1. ALWAYS get claim details first before any other operation
2. ALWAYS use the search_judge_pipeline for searching and confidence assessment

    - **IF** `judge_verdict` has decision="AUTO_SUBMIT" **AND** `composed_email` is present:
    - **OR IF** pipeline returns "Ready for email sending":
      **YOU MUST CALL `send_email` with:**
        - to_address: from composed_email
        - subject: from composed_email
        - body: from composed_email
        - cc_address: user_email from claim_details
        - reply_to: user_email from claim_details
        - image_url: image_url from composed_email (or receipt_image_url from claim_details)
      
      **AFTER sending email, YOU MUST CALL `update_claim_status` with:**
        - status="SUBMITTED"
        - actions_taken=["Composed email", "Sent email to [address]", "Copied user"]
        - email_body=body from composed_email
        - contact_details=web_search_result (if available)

4. NEVER send emails directly - only compose via writer_agent then use send_email tool
5. ALWAYS update claim status before returning to user. The task is NOT DONE until `update_claim_status` is called.
6. NEVER fabricate support email addresses
7. Confidence threshold for auto-submit is {confidence_threshold}
   (that's {confidence_threshold_percent}%)
8. For AUTO_SUBMIT flow: ALWAYS trigger writer_agent, then send_email, then update status
9. For AUTO_SUBMIT flow: ALWAYS include email preview in response to user
10. Store support_email_used, confidence_score, and judge_reasoning in status update
11. For HUMAN_REVIEW: NEVER trigger writer_agent when confidence < threshold
12. For HUMAN_REVIEW: ALWAYS update status to PENDING with attempted_emails
13. For HUMAN_REVIEW: ALWAYS include pending_reason for audit trail
14. For HUMAN_REVIEW: Return user message about queued for verification
15. For REQUIRES_REVIEW: DETECT no email found when recommended_email is empty/null
16. For REQUIRES_REVIEW: NEVER trigger writer_agent when no email is found
17. For REQUIRES_REVIEW: ALWAYS update status to REQUIRES_REVIEW (not PENDING)
18. For REQUIRES_REVIEW: Set confidence_score to 0.0 (zero confidence with no email)
19. For REQUIRES_REVIEW: Include search attempts in judge_reasoning for audit trail
20. For REQUIRES_REVIEW: Return message mentioning brand name and specialist assistance

STOP: Do not return to the user until you have called `update_claim_status`.
If you see "Ready for email sending", it means YOU must now send the email.
"""


def build_root_instruction() -> str:
    """
    Build the root agent instruction with actual configuration values.

    This function interpolates the confidence threshold from settings into the
    instruction template. Dynamic content is placed at the end to maximize
    Gemini prompt caching for the static content.

    Returns:
        str: The complete instruction string with threshold values.
    """
    threshold = settings.confidence_threshold
    threshold_percent = int(threshold * 100)

    return ROOT_AGENT_INSTRUCTION.format(
        confidence_threshold=threshold,
        confidence_threshold_percent=threshold_percent,
    )


# =============================================================================
# CALLBACK FUNCTIONS
# =============================================================================


async def before_agent_callback(
    callback_context: CallbackContext,
) -> types.Content | None:
    """
    Validate user_id and claim_id are present in session state.

    This callback runs before the agent processes each request to ensure
    required context is available.

    Args:
        callback_context: ADK callback context with session state access.

    Returns:
        None if validation passes, or Content with error if validation fails.
    """
    state = callback_context.state

    # Check for user_id
    user_id = state.get("user_id")
    if not user_id:
        logger.warning("before_agent_callback: user_id not found in state")
        # We don't block - just log warning, as user_id may be optional
        # in some deployment scenarios

    # Check for claim_id
    claim_id = state.get("claim_id")
    if not claim_id:
        logger.warning("before_agent_callback: claim_id not found in state")
        # Similarly, we log but don't block - the user message may contain
        # the claim_id to process

    logger.info(
        "before_agent_callback: user_id=%s, claim_id=%s",
        user_id,
        claim_id,
    )

    # Return None to continue processing
    return None


# =============================================================================
# ROOT AGENT DEFINITION
# =============================================================================

root_agent = LlmAgent(
    name="clara_care_orchestrator",
    model=settings.model_name,
    description=f"""Root orchestrator for ClaraCare warranty claim processing.

    USE FOR:
    - Processing warranty claims end-to-end
    - Coordinating search, judge, and routing workflows
    - Managing claim status throughout the process

    WORKFLOW:
    1. Get claim details
    2. Search for support contacts (parallel DB + web)
    3. Judge confidence in results
    4. Route based on results:
        - AUTO_SUBMIT (>= {int(settings.confidence_threshold * 100)}% confidence)
        - HUMAN_REVIEW (< {int(settings.confidence_threshold * 100)}% confidence)
        - REQUIRES_REVIEW (no email found)

    AUTO_SUBMIT FLOW (US-015):
    - When confidence >= {settings.confidence_threshold}: 
    - OR when pipeline says "Ready for email sending. Email composed and verified.":
    - CHECK for composed_email from pipeline
    - MUST EXECUTE send_email
    - MUST EXECUTE update_claim_status to submitted with actions_taken, email_body, and contact_details (from web_search_result)
    - Return confirmation with email preview and actions taken

    HUMAN_REVIEW FLOW (US-016):
    - When confidence < {settings.confidence_threshold}:
    - MUST EXECUTE update_claim_status to pending
    - Return message: "Your claim requires additional verification..."

    REQUIRES_REVIEW FLOW (US-017):
    - When NO email found:
    - MUST EXECUTE update_claim_status to requires_review
    - Return message: "We could not find support contact for [brand]..."

    THRESHOLD: {settings.confidence_threshold} confidence for auto-submit
    CRITICAL: ALWAYS update database status before returning to user.
    If pipeline returns "Ready for email sending. Email composed and verified.", you MUST send the email.
    """,
    instruction=build_root_instruction(),
    tools=[
        get_claim_details,
        email_tool.send_email,
        update_claim_status,
    ],
    sub_agents=[
        search_judge_pipeline,
    ],
    before_agent_callback=before_agent_callback,
)
