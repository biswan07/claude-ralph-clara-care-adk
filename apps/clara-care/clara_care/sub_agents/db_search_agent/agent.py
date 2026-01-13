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

## SEARCH STRATEGY

- Use the exact brand name first (e.g., "Sony")
- If no results, try common variations (e.g., "Sony Electronics")
- Consider the product category if provided to narrow results

## OUTPUT FORMAT

You MUST respond with a JSON object in exactly this format:
```json
{
  "found": true/false,
  "email": "support email address or null",
  "confidence": 0.0-1.0 confidence score,
  "source": "internal_db",
  "brand_name": "matched brand name",
  "additional_contacts": {
    "phone": "phone number or null",
    "url": "support URL or null"
  }
}
```

## EXAMPLES

### Example 1: Brand Found
User: "Find support contact for Sony television"
- You call: search_support_contacts(brand_name="Sony", product_category="Electronics")
- Database returns a match with support@sony.com, confidence 0.95

Your response:
```json
{
  "found": true,
  "email": "support@sony.com",
  "confidence": 0.95,
  "source": "internal_db",
  "brand_name": "Sony",
  "additional_contacts": {
    "phone": "1-800-222-7669",
    "url": "https://www.sony.com/support"
  }
}
```

### Example 2: Brand Not Found
User: "Find support contact for UnknownBrand laptop"
- You call: search_support_contacts(brand_name="UnknownBrand")
- Database returns no results

Your response:
```json
{
  "found": false,
  "email": null,
  "confidence": 0.0,
  "source": "internal_db",
  "brand_name": "UnknownBrand",
  "additional_contacts": null
}
```

## IMPORTANT RULES

- ALWAYS use the search_support_contacts tool - never guess email addresses
- Return the FIRST and BEST match if multiple results exist
- Include confidence score from database results
- Set source to "internal_db" always
- If database search fails with error, set found=false with confidence=0.0
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
