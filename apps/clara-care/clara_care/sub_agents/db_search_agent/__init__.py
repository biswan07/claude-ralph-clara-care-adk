"""Internal database search agent for warranty support contacts.

This sub-agent searches the internal support contacts database
for known manufacturer support information.
"""

from .agent import db_search_agent

__all__ = ["db_search_agent"]
