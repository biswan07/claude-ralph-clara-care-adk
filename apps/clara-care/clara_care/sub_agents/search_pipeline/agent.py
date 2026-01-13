"""Parallel search pipeline for finding manufacturer support contacts.

This pipeline executes the internal database search and web search agents
concurrently. Both agents write to their own unique output_keys in session
state, allowing downstream agents to read the results.
"""

from google.adk.agents import ParallelAgent

from clara_care.sub_agents.db_search_agent import db_search_agent
from clara_care.sub_agents.web_search_agent import web_search_agent

# =============================================================================
# PARALLEL SEARCH PIPELINE
# =============================================================================

search_pipeline = ParallelAgent(
    name="search_pipeline",
    description="""Parallel search pipeline for support contacts.

    Executes internal database search and web search concurrently:
    - db_search_agent: Searches internal support_contacts table
      → writes to state["internal_search_result"]
    - web_search_agent: Searches web for manufacturer support emails
      → writes to state["web_search_result"]

    USE FOR:
    - Initial search phase of warranty claim processing
    - Finding support contacts from multiple sources simultaneously
    - Gathering all available data before confidence assessment

    OUTPUTS:
    - internal_search_result: JSON with found, email, confidence, source
    - web_search_result: JSON with found, emails (list), sources
    """,
    sub_agents=[
        db_search_agent,
        web_search_agent,
    ],
)
