"""Root orchestrator agent for ClaraCare warranty claim processing.

This module defines the root agent that coordinates the entire warranty
claim workflow: search -> judge -> route (auto-submit or human queue).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google.adk.agents import LlmAgent

from clara_care.config import settings
from clara_care.sub_agents import search_judge_pipeline, writer_agent
from clara_care.tools import get_claim_details, update_claim_status

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

The pipeline will provide:
- internal_search_result: Results from internal database
- web_search_result: Results from web search with validation
- judge_verdict: Confidence assessment with recommended email and decision

### Step 3: Route Based on Confidence

**HIGH CONFIDENCE (>= 0.80)**: AUTO_SUBMIT flow
- The judge_verdict.decision will be "AUTO_SUBMIT"
- Delegate to `writer_agent` to compose a professional warranty claim email
- Update claim status to SUBMITTED using `update_claim_status`
- Return confirmation with email preview to user

**LOW CONFIDENCE (< 0.80)**: HUMAN_REVIEW flow
- The judge_verdict.decision will be "HUMAN_REVIEW"
- Do NOT compose or send any email
- Update claim status to PENDING with reason: "Low confidence - requires human
  verification"
- Return message: "Your claim requires additional verification and has been
  queued for review"

**NO EMAIL FOUND**: REQUIRES_REVIEW flow
- Neither search found a valid email
- Update claim status to REQUIRES_REVIEW
- Return message: "We could not find support contact information for [brand].
  A support specialist will assist you."

## TOOLS AVAILABLE

1. `get_claim_details(claim_id)` - Retrieve full claim information
2. `update_claim_status(claim_id, status, support_email_used, confidence_score,
   judge_reasoning)` - Update claim status for tracking

## SUB-AGENTS AVAILABLE

1. `search_judge_pipeline` - Searches for support contacts and assesses confidence
2. `writer_agent` - Composes professional warranty claim emails

## STATE KEYS

After processing, these keys will be in session state:
- `claim_details`: Full claim information (you set this after get_claim_details)
- `internal_search_result`: Internal DB search results (from search_judge_pipeline)
- `web_search_result`: Web search results (from search_judge_pipeline)
- `judge_verdict`: Confidence assessment and decision (from search_judge_pipeline)
- `composed_email`: Composed email content (from writer_agent, if auto-submit)

## RESPONSE FORMAT

Always respond with a clear summary for the user:

For AUTO_SUBMIT:
```
Your warranty claim [claim_id] has been submitted to [brand] support.

Email sent to: [support_email]
Subject: [subject]

Confidence Score: [score]%

We will notify you when we receive a response.
```

For HUMAN_REVIEW:
```
Your warranty claim [claim_id] requires additional verification.

We found potential support contacts but could not verify them with high
confidence. Your claim has been queued for review by our support team.

Expected response time: 24-48 hours
```

For REQUIRES_REVIEW:
```
Your warranty claim [claim_id] requires specialist assistance.

We could not find support contact information for [brand].
A support specialist will assist you with this claim.

Expected response time: 24-48 hours
```

## IMPORTANT RULES

1. ALWAYS get claim details first before any other operation
2. ALWAYS use the search_judge_pipeline for searching and confidence assessment
3. NEVER send emails directly - only compose via writer_agent
4. ALWAYS update claim status before returning to user
5. NEVER fabricate support email addresses
6. Confidence threshold for auto-submit is 0.80 (80%)
"""

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
    description="""Root orchestrator for ClaraCare warranty claim processing.

    USE FOR:
    - Processing warranty claims end-to-end
    - Coordinating search, judge, and routing workflows
    - Managing claim status throughout the process

    WORKFLOW:
    1. Get claim details
    2. Search for support contacts (parallel DB + web)
    3. Judge confidence in results
    4. Route: AUTO_SUBMIT (>= 80%) or HUMAN_REVIEW (< 80%)

    THRESHOLD: 0.80 confidence for auto-submit
    """,
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        get_claim_details,
        update_claim_status,
    ],
    sub_agents=[
        search_judge_pipeline,
        writer_agent,
    ],
    before_agent_callback=before_agent_callback,
)
