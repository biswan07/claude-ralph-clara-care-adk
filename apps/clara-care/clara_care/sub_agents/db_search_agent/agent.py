"""Internal database search agent for finding known support contacts.

This agent searches the internal support contacts database to find
manufacturer warranty support emails, phones, and URLs. It should be
used as the first search source before web search.
"""

from google.adk.agents import LlmAgent

from clara_care.config import settings
from clara_care.tools import search_support_contacts

# =============================================================================
# STATIC INSTRUCTION CONTENT (CACHEABLE)
# =============================================================================

DB_SEARCH_AGENT_INSTRUCTION = """You are an internal database search specialist.
Your job is to search the internal support contacts database to find known
manufacturer warranty support contact information.

## YOUR TASK

When given a warranty claim with a brand/manufacturer name:
1. Search the internal database using the search_support_contacts tool
2. If found, extract and return the support contact information
3. If not found, clearly indicate no internal record exists

## SEARCH STRATEGY (SINGLE SHOT)

1. **ONE SEARCH ONLY**: You have exactly *ONE* chance to find the contact.
2. **USE SHORT NAME**: Search for the simplest version of the brand name (e.g., use "Sony" not "Sony Corporation").
3. **WILDCARD IS AUTOMATIC**: The system automatically applies `%...%` wildcards. Searching "Sony" *will* match "Sony Electronics" and "Sony Support".
4. **NO RETRIES**: If the first search returns `found: false`, STOP and return that result immediately. Do NOT try variations. Do NOT try different categories.

## EXAMPLE
User: "Find support for DJI Drone"
- You call: `search_support_contacts(brand_name="DJI", product_category="Drone")`
- If not found -> Return `found: false` immediately. Do not try "DJI Technology".
"""

# =============================================================================
# AGENT DEFINITION
# =============================================================================

db_search_agent = LlmAgent(
    name="db_search_agent",
    model=settings.model_name,
    description="""Internal database search specialist.

    USE FOR:
    - Finding known manufacturer support contacts
    - Querying the internal support_contacts table
    - First-pass search before web search fallback

    RETURNS: JSON with found, email, confidence, source
    """,
    instruction=DB_SEARCH_AGENT_INSTRUCTION,
    tools=[search_support_contacts],
    output_key="internal_search_result",
)
