"""Pytest configuration and fixtures for ClaraCare tests.

This module sets up environment variables before any imports to allow
testing without requiring actual credentials.
"""

from __future__ import annotations

import os
import sys

# Set required environment variables BEFORE any clara_care imports
# This must happen at conftest load time to ensure settings validation passes
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")

# Clear any cached modules to ensure fresh imports with test env vars
modules_to_clear = [k for k in sys.modules.keys() if k.startswith("clara_care")]
for module in modules_to_clear:
    del sys.modules[module]
