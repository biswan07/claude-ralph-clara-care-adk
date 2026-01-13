"""Supabase client module for ClaraCare agent.

Provides a singleton Supabase client instance for database operations.
Uses the service role key for backend operations with full access.
"""

import logging
from functools import lru_cache

from supabase import Client, create_client

from clara_care.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseConnectionError(Exception):
    """Raised when Supabase connection fails."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get or create a singleton Supabase client instance.

    Uses lru_cache to ensure only one client instance is created.
    The service role key provides full backend access to the database.

    Returns:
        Client: Supabase client instance.

    Raises:
        SupabaseConnectionError: If connection to Supabase fails.
    """
    try:
        settings = get_settings()
        client: Client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_role_key,
        )
        logger.info("Supabase client initialized successfully")
        return client
    except ValueError as e:
        logger.error("Invalid Supabase configuration: %s", e)
        raise SupabaseConnectionError(
            f"Invalid Supabase configuration: {e}"
        ) from e
    except Exception as e:
        logger.error("Failed to connect to Supabase: %s", e)
        raise SupabaseConnectionError(
            f"Failed to connect to Supabase: {e}"
        ) from e


# Lazy singleton - client is created on first access via get_supabase_client()
# This pattern allows the module to be imported without triggering connection,
# enabling testing without full configuration.
supabase_client: Client | None = None


def get_client() -> Client:
    """Get the Supabase client instance.

    This is the recommended way to access the client. It provides lazy
    initialization and proper error handling.

    Returns:
        Client: Supabase client instance.

    Raises:
        SupabaseConnectionError: If connection to Supabase fails.
    """
    global supabase_client
    if supabase_client is None:
        supabase_client = get_supabase_client()
    return supabase_client
