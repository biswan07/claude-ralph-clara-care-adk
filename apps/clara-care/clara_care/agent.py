"""Root orchestrator agent for ClaraCare warranty claim processing.

This module defines the root agent that coordinates the entire warranty
claim workflow: search -> judge -> route (auto-submit or human queue).
"""

from google.adk.agents import LlmAgent

from clara_care.config import settings

# Placeholder root agent - will be fully implemented in US-014
root_agent = LlmAgent(
    name="clara_care_orchestrator",
    model=settings.model_name,
    instruction="""You are ClaraCare, an AI assistant that helps users process
    warranty claims. You coordinate searching for manufacturer support contacts,
    assessing confidence in found contacts, and routing claims appropriately.

    For high-confidence results (>= 80%), claims are auto-submitted.
    For low-confidence results, claims are queued for human review.
    """,
    description="Root orchestrator for warranty claim processing",
)
