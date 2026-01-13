"""ClaraCare Warranty Claim Agent.

Multi-agent warranty claim system built on Google ADK that searches for
manufacturer support contacts, assesses confidence, and routes claims
to auto-submit or human review.
"""

from clara_care.agent import root_agent

__all__ = ["root_agent"]
