"""Search and judge sequential pipeline for warranty claim processing.

This pipeline executes a sequential workflow:
1. First, the parallel search pipeline runs (db_search + web_search concurrently)
2. Then, the judge agent assesses confidence based on all search results

The judge agent reads the search results via state placeholders:
- {internal_search_result}: From db_search_agent
- {web_search_result}: From web_search_agent

The final verdict is written to state["judge_verdict"].
"""

from google.adk.agents import SequentialAgent

from clara_care.sub_agents.judge_agent import judge_agent
from clara_care.sub_agents.search_pipeline import search_pipeline
from clara_care.sub_agents.submission_agent import submission_agent
from clara_care.sub_agents.writer_agent import writer_agent

# =============================================================================
# SEQUENTIAL SEARCH & JUDGE PIPELINE
# =============================================================================

search_judge_pipeline = SequentialAgent(
    name="search_judge_pipeline",
    description="""Sequential search-judge-compose-finalize pipeline.

    WORKFLOW:
    Step 1 - Parallel Search (search_pipeline):
      - db_search_agent: Searches internal database → internal_search_result
      - web_search_agent: Searches web and validates emails → web_search_result

    Step 2 - Judge (judge_agent):
      - Calculates confidence score
      - Decides: AUTO_SUBMIT or HUMAN_REVIEW
      → judge_verdict
    
    Step 3 - Composer (writer_agent):
      - Checks judge_verdict
      - IF AUTO_SUBMIT: Composes email → composed_email
      - IF NOT AUTO_SUBMIT: Skips

    Step 4 - Final Submission (submission_agent):
      - Reads judge_verdict and composed_email
      - GUARANTEED: Updates database status (submitted, pending, or requires_review)

    USE FOR:
    - Complete end-to-end processing for warranty claims
    - GUARANTEED execution of database status updates
    
    OUTPUTS IN STATE:
    - internal_search_result, web_search_result
    - judge_verdict
    - composed_email (if auto-submit)
    - claim_details
    """,
    sub_agents=[
        search_pipeline,  # Step 1: Parallel search (DB + Web)
        judge_agent,      # Step 2: Confidence assessment
        writer_agent,     # Step 3: Conditional email composition
        submission_agent, # Step 4: Finalize status
    ],
)
