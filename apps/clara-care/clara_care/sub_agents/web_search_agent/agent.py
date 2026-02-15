"""Web search agent for finding manufacturer support contacts via web.

This agent searches the web for warranty support email addresses when
the internal database doesn't have the information. It uses Google
Search to find emails and then validates them for legitimacy.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search  # type: ignore[attr-defined]

from clara_care.config import settings
from clara_care.tools import search_support_email, validate_email

# =============================================================================
# STATIC INSTRUCTION CONTENT (CACHEABLE)
# =============================================================================

WEB_SEARCH_AGENT_INSTRUCTION = """You are a web search specialist for finding \
manufacturer warranty support contacts.

Your job is to search the web for warranty support email addresses when the
internal database does not have the information. You must also validate any
emails you find to ensure they are legitimate.

## YOUR TASK

When asked to find support contact for a brand/manufacturer:
1. Use search_support_email to construct a targeted search query
2. Use google_search to execute the web search
3. Parse results to extract email addresses using search_support_email again
4. Validate found emails using validate_email tool
5. Return the best validated email(s) with scores

## SEARCH STRATEGY

1. **Initial Search**: Use search_support_email with the brand name to get
   the recommended search query
2. **Execute Search**: Use google_search with the query from step 1
3. **Extract Emails**: Call search_support_email again with raw results stored
   in your context, or manually extract email addresses from search results
4. **Extract Phone**: Extract any support phone numbers found in the search results
5. **Validate Each Email**: Use validate_email for each found email to check:
   - Format validity (RFC 5322 compliance)
   - Domain existence (MX records)
   - Brand domain match (e.g., support@sony.com for Sony)
   - Suspicious patterns (free email, odd TLDs)

## OUTPUT FORMAT

You MUST respond with a JSON object in exactly this format:
```json
{
  "found": true/false,
  "emails": [
    {
      "email": "support@brand.com",
      "validation_score": 0.95,
      "domain_matches_brand": true,
      "is_valid": true,
      "source_url": "https://brand.com/support",
      "phone": "1-800-555-0199"
    }
  ],
  "sources": ["list of source URLs where emails were found"],
  "search_query": "the query that was used",
  "brand_searched": "the brand name that was searched"
}
```

## EXAMPLES

### Example 1: Email Found and Validated
User: "Search web for Samsung warranty support email"

Step 1 - Get search query:
- Call: search_support_email(brand_name="Samsung", product_type="")
- Result: {"search_query": "Samsung warranty support email contact", ...}

Step 2 - Execute web search:
- Call: google_search("Samsung warranty support email contact")
- Result: Search results mentioning support@samsung.com

Step 3 - Validate the email:
- Call: validate_email(email="support@samsung.com", brand_name="Samsung")
- Result: {"is_valid": true, "validation_score": 0.92, ...}

Your response:
```json
{
  "found": true,
  "emails": [
    {
      "email": "support@samsung.com",
      "validation_score": 0.92,
      "domain_matches_brand": true,
      "is_valid": true,
      "source_url": "https://samsung.com/support",
      "phone": "1-800-726-7864"
    }
  ],
  "sources": ["https://samsung.com/support"],
  "search_query": "Samsung warranty support email contact",
  "brand_searched": "Samsung"
}
```

### Example 2: Multiple Emails Found
User: "Search web for LG appliance warranty support"

After searching and validating, you find two emails with different scores.

Your response:
```json
{
  "found": true,
  "emails": [
    {
      "email": "warranty@lg.com",
      "validation_score": 0.88,
      "domain_matches_brand": true,
      "is_valid": true,
      "source_url": "https://lg.com/support/warranty"
    },
    {
      "email": "support@lgservice.com",
      "validation_score": 0.65,
      "domain_matches_brand": true,
      "is_valid": true,
      "source_url": "https://lg.com/contact"
    }
  ],
  "sources": ["https://lg.com/support/warranty", "https://lg.com/contact"],
  "search_query": "LG appliance warranty support email contact",
  "brand_searched": "LG"
}
```

### Example 3: No Valid Email Found
User: "Search web for ObscureBrand support email"

After searching, no valid emails are found.

Your response:
```json
{
  "found": false,
  "emails": [],
  "sources": [],
  "search_query": "ObscureBrand warranty support email contact",
  "brand_searched": "ObscureBrand"
}
```

## IMPORTANT RULES

1. **ALWAYS validate emails**: Never return an email without running validate_email
2. **Prioritize by validation score**: List emails in order of validation_score
3. **Filter low scores**: Only include emails with validation_score >= 0.3
4. **Never guess emails**: Only return emails actually found in search results
5. **Include source URLs**: Track where each email was found for audit trail
6. **Check brand match**: Prefer emails where domain_matches_brand is true
7. **Handle failures gracefully**: If search fails, return found=false with empty arrays

## VALIDATION SCORE INTERPRETATION

- **0.9-1.0**: High confidence - domain matches brand, MX records exist
- **0.7-0.89**: Good confidence - likely legitimate but some concerns
- **0.5-0.69**: Medium confidence - may need human verification
- **0.3-0.49**: Low confidence - significant concerns
- **<0.3**: Too low - do not include in results
"""

# =============================================================================
# WEB SEARCH EXECUTION AGENT
# =============================================================================

WEB_SEARCH_EXECUTOR_INSTRUCTION = """You are a web search specialist.
Your ONLY job is to search for manufacturer warranty support contacts.

1.  Identify the Product Brand from `claim_details` in the session state.
2.  Construct a **SINGLE** targeted search query like: "[Brand] warranty support email".
3.  Use the `google_search` tool **ONCE**.
4.  Output the search results directly.
5.  **DO NOT RETRY**. If the first search doesn't yield perfect results, pass whatever you found to the next agent.

"""

web_search_executor_agent = LlmAgent(
    name="web_search_executor",
    model=settings.model_name,
    description="Executes Google Search for support contacts.",
    instruction=WEB_SEARCH_EXECUTOR_INSTRUCTION,
    tools=[google_search],
    output_key="web_search_raw_results",
)

# =============================================================================
# WEB SEARCH PROCESSING AGENT
# =============================================================================

WEB_SEARCH_PROCESSOR_INSTRUCTION = """You are a data extraction specialist.
Your job is to extract and validate emails from the search results provided by the previous agent.

1.  Read the search results from the previous step (or from `web_search_raw_results` in state).
2.  Use `search_support_email` (this tool can extract emails from text) to parse the results.
3.  Extract any **support phone numbers** found in the text.
4.  Use `validate_email` to check each found email.
5.  Return the final JSON object, including the phone number in the email objects if found.

## OUTPUT FORMAT
You MUST respond with a JSON object in exactly this format:
```json
{
  "found": true/false,
  "emails": [
    {
      "email": "support@brand.com",
      "validation_score": 0.95,
      "domain_matches_brand": true,
      "is_valid": true,
      "source_url": "https://brand.com/support",
      "phone": "1-800-555-0199"
    }
  ],
  "sources": ["list of source URLs"],
  "search_query": "the query used",
  "brand_searched": "the brand name"
}
```
"""

web_search_processor_agent = LlmAgent(
    name="web_search_processor",
    model=settings.model_name,
    description="Extracts and validates emails from search results.",
    instruction=WEB_SEARCH_PROCESSOR_INSTRUCTION,
    tools=[search_support_email, validate_email],
    output_key="web_search_result",
)

# =============================================================================
# AGENT DEFINITION (SEQUENTIAL PIPELINE)
# =============================================================================

from google.adk.agents import SequentialAgent

web_search_agent = SequentialAgent(
    name="web_search_agent",
    description="""Web search specialist for finding support contacts.
    
    Sequential Pipeline:
    1. Executor: Searches Google for support contacts
    2. Processor: Extracts and validates emails from search results
    
    RETURNS: JSON with found, emails (list with validation scores), sources
    """,
    sub_agents=[web_search_executor_agent, web_search_processor_agent],
)
