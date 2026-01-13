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

# =============================================================================
# SEQUENTIAL SEARCH & JUDGE PIPELINE
# =============================================================================

search_judge_pipeline = SequentialAgent(
    name="search_judge_pipeline",
    description="""Sequential search-then-judge pipeline for warranty claims.

    WORKFLOW:
    Step 1 - Parallel Search (search_pipeline):
      - db_search_agent: Searches internal database → internal_search_result
      - web_search_agent: Searches web and validates emails → web_search_result

    Step 2 - Judge (judge_agent):
      - Reads {internal_search_result} and {web_search_result} from state
      - Calculates confidence score using weighted factors
      - Decides: AUTO_SUBMIT (>= 0.80) or HUMAN_REVIEW (< 0.80)
      → judge_verdict

    USE FOR:
    - Complete search-and-assess workflow for warranty claims
    - When you need both search results AND a confidence verdict

    OUTPUTS IN STATE:
    - internal_search_result: Internal DB search results (JSON)
    - web_search_result: Web search results with validation (JSON)
    - judge_verdict: Final confidence verdict with decision (JSON)
    """,
    sub_agents=[
        search_pipeline,  # Step 1: Parallel search (DB + Web)
        judge_agent,      # Step 2: Confidence assessment
    ],
)
