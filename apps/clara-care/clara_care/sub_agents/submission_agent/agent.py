from google.adk.agents import LlmAgent
from clara_care.config import settings
from clara_care.tools.claim_status import update_claim_status
from clara_care.tools.email_tool import send_email

# =============================================================================
# SUBMISSION AGENT
# =============================================================================

SUBMISSION_INSTRUCTION = """You are the Submission Specialist.
Your ONLY job is to update the database status based on the Judge's Verdict.

1. READ 'judge_verdict', 'composed_email', and 'claim_details' from the session state.

IF decision is "AUTO_SUBMIT":
   - CHECK if 'composed_email' exists.
   - EXTRACT 'email' from the 'user' object in 'claim_details' (as fallback).
   - DETERMINE 'cc_address' and 'reply_to':
       - Use 'cc_address'/'reply_to' from 'composed_email' if available.
       - OTHERWISE use the extracted user email.
   - MUST EXECUTE send_email with:
       - to_address: (from composed_email)
       - subject: (from composed_email)
       - body: (from composed_email)
       - html_body: (from composed_email["html_body"])
       - cc_address: (the determined cc_address)
       - reply_to: (the determined reply_to)
   - MUST EXECUTE update_claim_status to submitted with actions_taken, email_body, and contact_details (from web_search_result)
   - RETURN a message: "Email sent and status updated."

IF decision is "HUMAN_REVIEW" (or "REQUIRES_REVIEW"):
   - CHECK if 'composed_email' exists.
   - CALL 'update_claim_status' with:
       - status="pending"
       - email_body=(from composed_email['body'] if exists)
       - email_html_body=(from composed_email['html_body'] if exists)
       - receipt_image_url=(from composed_email['image_url'] if exists)
       - support_email_used=(from composed_email['to_address'] OR judge_verdict['recommended_email'])
       - confidence_score=(from judge_verdict['confidence_score'])
   - RETURN a message: "Claim queued for manual review."

CRITICAL:
- For AUTO_SUBMIT: You MUST call 'update_claim_status' with status="submitted" and send_email.
- For HUMAN_REVIEW: You MUST call 'update_claim_status' with the composed email data to populate the review queue.
- Do NOT compose emails yourself; they have already been composed.
"""

submission_agent = LlmAgent(
    name="submission_agent",
    model=settings.model_name,
    description="Finalizes claim: updates DB status based on verdict.",
    instruction=SUBMISSION_INSTRUCTION,
    tools=[send_email,update_claim_status]
)
