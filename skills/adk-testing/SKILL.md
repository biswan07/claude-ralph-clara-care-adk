---
name: adk-testing
description: Test and evaluate Google ADK agents including unit tests, integration tests, and evaluation metrics. Use when user says "test agent", "agent testing", "evaluate agent", "unit test", or needs to verify agent behavior.
---

# ADK Testing & Evaluation Skill

## Purpose
Create comprehensive tests for ADK agents including unit tests, integration tests, and evaluation frameworks. Testing agents requires unique approaches different from traditional software testing.

## When to Activate
Activate when user mentions:
- "test agent", "agent testing", "unit test"
- "evaluate agent", "agent evaluation"
- "integration test", "end-to-end test"
- "mock tools", "test fixtures"
- "regression test", "verify behavior"

## Testing Challenges for Agents

| Challenge | Description | Solution |
|-----------|-------------|----------|
| Non-deterministic | LLM outputs vary | Test patterns, not exact matches |
| External dependencies | APIs, databases | Mock tools and services |
| Multi-agent complexity | Agent interactions | Test agents in isolation first |
| State management | Session state flow | Test state transitions |
| Async execution | Async agent calls | Use pytest-asyncio |

---

## Test Project Structure

```
apps/<agent-name>/
├── <agent_package>/
│   ├── __init__.py
│   ├── agent.py
│   ├── config.py
│   └── tools.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_tools.py     # Tool unit tests
│   │   ├── test_agents.py    # Agent unit tests
│   │   └── test_config.py    # Config tests
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_workflows.py # Multi-agent tests
│   │   └── test_state.py     # State flow tests
│   └── evaluation/
│       ├── __init__.py
│       ├── test_quality.py   # Output quality tests
│       └── eval_datasets/    # Evaluation datasets
│           └── test_cases.json
├── pyproject.toml
└── pytest.ini
```

---

## pytest Configuration

### pyproject.toml
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--asyncio-mode=auto",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
    "evaluation: Evaluation tests",
]

[dependency-groups]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
]
```

### pytest.ini (Alternative)
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
```

---

## Test Fixtures (conftest.py)

```python
"""Shared test fixtures for ADK agent testing."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools import ToolContext


@pytest.fixture
def session_service():
    """Provide in-memory session service for testing."""
    return InMemorySessionService()


@pytest.fixture
def mock_tool_context():
    """Provide mock ToolContext with state dictionary."""
    context = MagicMock(spec=ToolContext)
    context.state = {}
    return context


@pytest.fixture
def sample_state():
    """Provide sample session state for testing."""
    return {
        "research_context": "Test research context",
        "user_preferences": {"language": "en"},
        "iteration_count": 0,
    }


@pytest.fixture
async def runner(session_service):
    """Provide configured runner for agent testing."""
    from my_agent_package import root_agent

    return Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="test_agent",
    )


@pytest.fixture
def mock_google_search():
    """Mock google_search tool."""
    async def mock_search(query: str) -> str:
        return f"Mock search results for: {query}"
    return mock_search


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for deterministic testing."""
    return MagicMock(
        text="Mock LLM response",
        candidates=[MagicMock(content=MagicMock(parts=[MagicMock(text="Mock response")]))],
    )
```

---

## Unit Testing Tools

### test_tools.py
```python
"""Unit tests for custom tools."""

import pytest
from unittest.mock import MagicMock
from my_agent_package.tools import save_data, get_data, process_input


class TestSaveDataTool:
    """Tests for save_data tool."""

    def test_save_data_success(self, mock_tool_context):
        """Test successful data saving."""
        result = save_data(
            key="test_key",
            value="test_value",
            tool_context=mock_tool_context,
        )

        assert "Successfully saved" in result
        assert mock_tool_context.state["test_key"] == "test_value"

    def test_save_data_overwrites(self, mock_tool_context):
        """Test that saving overwrites existing data."""
        mock_tool_context.state["test_key"] = "old_value"

        result = save_data(
            key="test_key",
            value="new_value",
            tool_context=mock_tool_context,
        )

        assert mock_tool_context.state["test_key"] == "new_value"

    def test_save_data_empty_key(self, mock_tool_context):
        """Test handling of empty key."""
        result = save_data(
            key="",
            value="test_value",
            tool_context=mock_tool_context,
        )

        assert "Error" in result or "" not in mock_tool_context.state


class TestGetDataTool:
    """Tests for get_data tool."""

    def test_get_existing_data(self, mock_tool_context):
        """Test retrieving existing data."""
        mock_tool_context.state["test_key"] = "test_value"

        result = get_data(key="test_key", tool_context=mock_tool_context)

        assert result == "test_value"

    def test_get_missing_data(self, mock_tool_context):
        """Test retrieving non-existent data."""
        result = get_data(key="missing_key", tool_context=mock_tool_context)

        assert "not found" in result.lower() or "no data" in result.lower()


class TestProcessInputTool:
    """Tests for process_input tool."""

    @pytest.mark.parametrize("input_value,expected", [
        ("hello", "HELLO"),
        ("Hello World", "HELLO WORLD"),
        ("", ""),
    ])
    def test_process_input_variations(self, input_value, expected, mock_tool_context):
        """Test various input processing scenarios."""
        result = process_input(text=input_value, tool_context=mock_tool_context)

        assert expected in result
```

---

## Unit Testing Agents

### test_agents.py
```python
"""Unit tests for ADK agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAgentConfiguration:
    """Test agent configuration and setup."""

    def test_agent_has_required_attributes(self):
        """Test that agent has all required attributes."""
        from my_agent_package import root_agent

        assert root_agent.name is not None
        assert root_agent.model is not None
        assert root_agent.instruction is not None

    def test_agent_description(self):
        """Test agent has meaningful description."""
        from my_agent_package import root_agent

        assert root_agent.description is not None
        assert len(root_agent.description) > 10

    def test_agent_tools_configured(self):
        """Test that agent has expected tools."""
        from my_agent_package import root_agent

        tool_names = [t.__name__ if callable(t) else t.name for t in root_agent.tools]
        assert "save_data" in tool_names or len(tool_names) > 0


class TestAgentInstruction:
    """Test agent instruction templates."""

    def test_instruction_has_placeholders(self):
        """Test that instruction uses state placeholders."""
        from my_agent_package import root_agent

        # Check for placeholder pattern
        instruction = root_agent.instruction
        assert "{" in instruction and "}" in instruction

    def test_instruction_has_clear_structure(self):
        """Test instruction has expected sections."""
        from my_agent_package import root_agent

        instruction = root_agent.instruction.lower()
        # Check for common instruction elements
        has_task = "task" in instruction or "goal" in instruction
        has_output = "output" in instruction or "return" in instruction
        assert has_task or has_output


class TestSubAgents:
    """Test sub-agent configuration."""

    def test_sequential_agent_order(self):
        """Test that sequential agent has correct sub-agent order."""
        from my_agent_package.sub_agents import research_pipeline

        sub_agent_names = [a.name for a in research_pipeline.sub_agents]

        # Verify expected order
        assert len(sub_agent_names) >= 2
        # Add specific order assertions based on your pipeline

    def test_parallel_agent_unique_keys(self):
        """Test that parallel agents have unique output_keys."""
        from my_agent_package.sub_agents import parallel_fetcher

        output_keys = [
            a.output_key
            for a in parallel_fetcher.sub_agents
            if hasattr(a, 'output_key') and a.output_key
        ]

        # All keys should be unique
        assert len(output_keys) == len(set(output_keys))
```

---

## Integration Testing

### test_workflows.py
```python
"""Integration tests for multi-agent workflows."""

import pytest
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner


@pytest.mark.integration
class TestAgentWorkflow:
    """Test complete agent workflows."""

    @pytest.fixture
    async def runner(self):
        """Create runner for integration tests."""
        from my_agent_package import root_agent

        session_service = InMemorySessionService()
        return Runner(
            agent=root_agent,
            session_service=session_service,
            app_name="integration_test",
        )

    @pytest.mark.asyncio
    async def test_basic_workflow(self, runner):
        """Test basic agent interaction."""
        response = await runner.run(
            user_id="test_user",
            session_id="test_session",
            message="Hello, what can you help me with?",
        )

        assert response is not None
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_state_persistence(self, runner):
        """Test that state persists across interactions."""
        # First interaction
        await runner.run(
            user_id="test_user",
            session_id="test_session",
            message="Remember that my name is Alice",
        )

        # Second interaction - should remember
        response = await runner.run(
            user_id="test_user",
            session_id="test_session",
            message="What is my name?",
        )

        # Agent should have access to previous context
        assert response is not None


@pytest.mark.integration
class TestStateFlow:
    """Test session state flow between agents."""

    @pytest.mark.asyncio
    async def test_output_key_saves_to_state(self):
        """Test that output_key saves agent output to state."""
        from my_agent_package.sub_agents import step1_agent

        session_service = InMemorySessionService()
        runner = Runner(
            agent=step1_agent,
            session_service=session_service,
            app_name="state_test",
        )

        await runner.run(
            user_id="test_user",
            session_id="test_session",
            message="Process this input",
        )

        # Get session and check state
        session = await session_service.get_session(
            app_name="state_test",
            user_id="test_user",
            session_id="test_session",
        )

        # Verify output was saved
        if step1_agent.output_key:
            assert step1_agent.output_key in session.state

    @pytest.mark.asyncio
    async def test_sequential_state_flow(self):
        """Test state flows through sequential agents."""
        from my_agent_package.sub_agents import research_pipeline

        session_service = InMemorySessionService()
        runner = Runner(
            agent=research_pipeline,
            session_service=session_service,
            app_name="sequential_test",
        )

        await runner.run(
            user_id="test_user",
            session_id="test_session",
            message="Start the pipeline",
        )

        session = await session_service.get_session(
            app_name="sequential_test",
            user_id="test_user",
            session_id="test_session",
        )

        # Verify all expected state keys exist
        expected_keys = ["step1_result", "step2_result", "final_result"]
        for key in expected_keys:
            assert key in session.state, f"Missing state key: {key}"
```

---

## Mocking External Dependencies

### test_with_mocks.py
```python
"""Tests with mocked external dependencies."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestWithMockedTools:
    """Test agents with mocked tools."""

    @pytest.mark.asyncio
    async def test_agent_with_mocked_search(self):
        """Test agent behavior with mocked google_search."""

        # Mock the google_search tool
        mock_search_results = "Mock search result: Company A, Company B"

        with patch("google.adk.tools.google_search") as mock_search:
            mock_search.return_value = mock_search_results

            from my_agent_package import root_agent
            from google.adk.sessions import InMemorySessionService
            from google.adk.runners import Runner

            runner = Runner(
                agent=root_agent,
                session_service=InMemorySessionService(),
                app_name="mock_test",
            )

            response = await runner.run(
                user_id="test",
                session_id="test",
                message="Search for competitors",
            )

            assert response is not None

    @pytest.mark.asyncio
    async def test_agent_with_mocked_api(self):
        """Test agent behavior with mocked API calls."""

        mock_api_response = {"status": "success", "data": [1, 2, 3]}

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                json=lambda: mock_api_response,
                status_code=200,
            )

            # Run agent that uses API
            # Assert expected behavior


class TestWithMockedLLM:
    """Test agent logic with mocked LLM responses."""

    @pytest.mark.asyncio
    async def test_tool_selection(self):
        """Test that agent selects correct tool."""

        # This tests the prompt/instruction logic
        # by examining what the agent tries to do
        pass

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test agent handles errors gracefully."""

        with patch("my_agent_package.tools.external_api") as mock_api:
            mock_api.side_effect = ConnectionError("Network error")

            # Run agent and verify error handling
            # Assert agent provides helpful error message
```

---

## Evaluation Testing

### test_quality.py
```python
"""Evaluation tests for agent output quality."""

import pytest
import json
from pathlib import Path


class TestOutputQuality:
    """Test agent output quality metrics."""

    @pytest.fixture
    def eval_dataset(self):
        """Load evaluation dataset."""
        dataset_path = Path(__file__).parent / "eval_datasets" / "test_cases.json"
        with open(dataset_path) as f:
            return json.load(f)

    @pytest.mark.evaluation
    @pytest.mark.asyncio
    async def test_response_relevance(self, eval_dataset, runner):
        """Test that responses are relevant to queries."""
        for test_case in eval_dataset["relevance_tests"]:
            response = await runner.run(
                user_id="eval_user",
                session_id=f"eval_{test_case['id']}",
                message=test_case["input"],
            )

            # Check for expected keywords
            for keyword in test_case["expected_keywords"]:
                assert keyword.lower() in response.text.lower(), (
                    f"Missing expected keyword '{keyword}' in response"
                )

    @pytest.mark.evaluation
    @pytest.mark.asyncio
    async def test_response_completeness(self, eval_dataset, runner):
        """Test that responses are complete."""
        for test_case in eval_dataset["completeness_tests"]:
            response = await runner.run(
                user_id="eval_user",
                session_id=f"eval_{test_case['id']}",
                message=test_case["input"],
            )

            # Check minimum response length
            min_length = test_case.get("min_length", 50)
            assert len(response.text) >= min_length, (
                f"Response too short: {len(response.text)} < {min_length}"
            )

            # Check for required sections
            for section in test_case.get("required_sections", []):
                assert section.lower() in response.text.lower(), (
                    f"Missing required section: {section}"
                )

    @pytest.mark.evaluation
    @pytest.mark.asyncio
    async def test_no_hallucination(self, eval_dataset, runner):
        """Test that agent doesn't hallucinate facts."""
        for test_case in eval_dataset["hallucination_tests"]:
            response = await runner.run(
                user_id="eval_user",
                session_id=f"eval_{test_case['id']}",
                message=test_case["input"],
            )

            # Check for forbidden patterns (known hallucination triggers)
            for forbidden in test_case.get("forbidden_patterns", []):
                assert forbidden.lower() not in response.text.lower(), (
                    f"Response contains forbidden pattern: {forbidden}"
                )


class TestToolUsage:
    """Test that agents use tools appropriately."""

    @pytest.mark.evaluation
    @pytest.mark.asyncio
    async def test_tool_called_when_needed(self, runner):
        """Test that agent calls tools when appropriate."""
        # Queries that should trigger tool use
        tool_requiring_queries = [
            "Search for the latest news about AI",
            "What is the current weather in Tokyo?",
        ]

        for query in tool_requiring_queries:
            # Run with tool call tracking
            # Assert tool was called
            pass

    @pytest.mark.evaluation
    @pytest.mark.asyncio
    async def test_no_unnecessary_tool_calls(self, runner):
        """Test that agent doesn't call tools unnecessarily."""
        simple_queries = [
            "What is 2 + 2?",
            "Say hello",
        ]

        for query in simple_queries:
            # Run with tool call tracking
            # Assert no external tool calls
            pass
```

### eval_datasets/test_cases.json
```json
{
  "relevance_tests": [
    {
      "id": "rel_001",
      "input": "What are the main competitors in the cloud computing market?",
      "expected_keywords": ["AWS", "Azure", "Google Cloud", "competitor"]
    },
    {
      "id": "rel_002",
      "input": "Explain the benefits of microservices architecture",
      "expected_keywords": ["scalability", "deployment", "service"]
    }
  ],
  "completeness_tests": [
    {
      "id": "comp_001",
      "input": "Provide a comprehensive analysis of market trends",
      "min_length": 200,
      "required_sections": ["trends", "analysis", "conclusion"]
    }
  ],
  "hallucination_tests": [
    {
      "id": "hal_001",
      "input": "What happened in the news yesterday?",
      "forbidden_patterns": ["I read that", "According to my knowledge"]
    }
  ]
}
```

---

## Running Tests

### Command Reference
```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run integration tests only
uv run pytest -m integration

# Run evaluation tests only
uv run pytest -m evaluation

# Run with coverage
uv run pytest --cov=my_agent_package --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_tools.py

# Run specific test class
uv run pytest tests/unit/test_tools.py::TestSaveDataTool

# Run specific test
uv run pytest tests/unit/test_tools.py::TestSaveDataTool::test_save_data_success

# Run with verbose output
uv run pytest -v

# Run and stop on first failure
uv run pytest -x

# Run last failed tests
uv run pytest --lf
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
# .github/workflows/test.yml
name: Test ADK Agent

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv sync --group test

      - name: Run unit tests
        run: uv run pytest -m unit --cov=my_agent_package

      - name: Run integration tests
        run: uv run pytest -m integration
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Testing Deployed Agents (Vertex AI Agent Engine)

### Deployed Agent Test Script

```python
"""Test a deployed agent on Vertex AI Agent Engine.

Usage:
    cd apps/<agent-name>
    uv run python scripts/test_deployed_agent.py
    uv run python scripts/test_deployed_agent.py --benchmark
    uv run python scripts/test_deployed_agent.py "Custom query here"
"""

import argparse
import asyncio
import time
from dataclasses import dataclass

import vertexai
from vertexai import agent_engines

# Configuration
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
RESOURCE_ID = "your-resource-id"
PROJECT_NUMBER = "your-project-number"
RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{RESOURCE_ID}"

# Test user (use a real user ID for RLS testing)
USER_ID = "test-user-uuid"

# Pre-warm query (lightweight to prime the cache)
PREWARM_QUERY = "ready"


@dataclass
class QueryResult:
    """Result of a single query execution."""
    query: str
    success: bool
    response: str = ""
    error: str = ""
    latency_ms: float = 0.0
    is_prewarm: bool = False


def extract_final_response(events: list) -> str:
    """Extract the final text response from streaming events.

    CRITICAL: Events have nested structure:
    event['content']['parts'][0]['text']
    """
    final_texts = []
    for event in events:
        if isinstance(event, dict):
            content = event.get("content", {})
            if isinstance(content, dict):
                parts = content.get("parts", [])
                for part in parts:
                    if isinstance(part, dict) and "text" in part:
                        final_texts.append(part["text"])
    return "\n".join(final_texts) if final_texts else "No text response found"


async def run_query(
    remote_app,
    session_id: str,
    query: str,
    verbose: bool = False,
) -> QueryResult:
    """Run a single query and return the result with timing."""
    start_time = time.perf_counter()
    events = []

    try:
        async for event in remote_app.async_stream_query(
            user_id=USER_ID,
            session_id=session_id,
            message=query,
        ):
            events.append(event)
            if verbose:
                print(f"  Event: {type(event)}")

        latency_ms = (time.perf_counter() - start_time) * 1000
        response = extract_final_response(events)

        return QueryResult(
            query=query,
            success=True,
            response=response,
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return QueryResult(
            query=query,
            success=False,
            error=str(e),
            latency_ms=latency_ms,
        )


async def prewarm_session(
    remote_app,
    session_id: str,
) -> QueryResult:
    """Send a lightweight query to prime the Gemini cache.

    Pre-warming reduces subsequent query latency by 20-30%.
    """
    print(f"\n[PRE-WARM] Sending warm-up query: '{PREWARM_QUERY}'")

    result = await run_query(remote_app, session_id, PREWARM_QUERY)
    result.is_prewarm = True

    if result.success:
        print(f"[PRE-WARM] Cache primed in {result.latency_ms:.0f}ms")
    else:
        print(f"[PRE-WARM] Failed: {result.error}")

    return result


async def main():
    """Test the deployed agent."""
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Get the deployed agent
    remote_app = agent_engines.get(RESOURCE_NAME)
    print(f"Agent: {remote_app.display_name}")

    # Create a session
    session = remote_app.create_session(user_id=USER_ID)
    session_id = session.get("id") if isinstance(session, dict) else session.id
    print(f"Session ID: {session_id}")

    # Pre-warm the cache
    await prewarm_session(remote_app, session_id)

    # Run test queries
    queries = [
        "What did I buy in 2024?",
        "How much did I spend at JB Hi-Fi?",
    ]

    for query in queries:
        result = await run_query(remote_app, session_id, query)
        print(f"\n{query}")
        print(f"Response: {result.response[:200]}...")
        print(f"Latency: {result.latency_ms:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Benchmarking Deployed Agents

### Benchmark Script with Statistics

```python
"""Benchmark deployed agent performance.

Runs multiple queries and calculates latency statistics.
"""

import asyncio
import time
from dataclasses import dataclass

import vertexai
from vertexai import agent_engines


BENCHMARK_QUERIES = [
    # SQL queries
    "What did I buy in 2024?",
    "How much did I spend at JB Hi-Fi?",
    "My most expensive purchase",
    "How many receipts do I have?",
    # Vector queries
    "Show me my Apple products",
    "Find my headphones",
    # Warranty queries
    "What warranties are expiring soon?",
]


@dataclass
class BenchmarkStats:
    """Benchmark statistics."""
    total_queries: int
    successful: int
    failed: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    prewarm_latency_ms: float | None


async def run_benchmark(
    remote_app,
    session_id: str,
    queries: list[str],
    enable_prewarm: bool = True,
) -> BenchmarkStats:
    """Run benchmark and return statistics."""
    results = []
    prewarm_result = None

    # Pre-warm if enabled
    if enable_prewarm:
        prewarm_result = await prewarm_session(remote_app, session_id)

    # Run all queries
    print("\n" + "=" * 70)
    print("BENCHMARK QUERIES")
    print("=" * 70)

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] {query}")
        result = await run_query(remote_app, session_id, query)
        results.append(result)

        status = "PASS" if result.success else "FAIL"
        print(f"  [{status}] {result.latency_ms:.0f}ms")

    # Calculate statistics
    successful = [r for r in results if r.success]

    if successful:
        latencies = [r.latency_ms for r in successful]
        stats = BenchmarkStats(
            total_queries=len(queries),
            successful=len(successful),
            failed=len(queries) - len(successful),
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=sorted(latencies)[len(latencies) // 2],
            prewarm_latency_ms=prewarm_result.latency_ms if prewarm_result else None,
        )
    else:
        stats = BenchmarkStats(
            total_queries=len(queries),
            successful=0,
            failed=len(queries),
            avg_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            p50_latency_ms=0,
            prewarm_latency_ms=None,
        )

    # Print summary
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total Queries:  {stats.total_queries}")
    print(f"Successful:     {stats.successful}")
    print(f"Failed:         {stats.failed}")
    print(f"\nLatency Statistics (excluding pre-warm):")
    print(f"  Average:      {stats.avg_latency_ms:.0f}ms ({stats.avg_latency_ms/1000:.2f}s)")
    print(f"  Min:          {stats.min_latency_ms:.0f}ms")
    print(f"  Max:          {stats.max_latency_ms:.0f}ms")
    print(f"  P50 (median): {stats.p50_latency_ms:.0f}ms")
    if stats.prewarm_latency_ms:
        print(f"\nPre-warm:       {stats.prewarm_latency_ms:.0f}ms")

    return stats
```

---

## Performance Testing Patterns

### Pre-warming for Cache Optimization

```python
"""Pre-warming pattern for deployed agents.

Pre-warming sends a lightweight query after session creation to:
1. Prime Gemini's prompt cache with static instruction content
2. Initialize database connections
3. Warm up embedding model connections

This reduces subsequent query latency by 20-30%.
"""

# Lightweight pre-warm query that exercises minimal processing
PREWARM_QUERY = "ready"  # Simple, fast to process

async def test_with_prewarm():
    """Test agent with pre-warming enabled."""
    remote_app = agent_engines.get(RESOURCE_NAME)
    session = remote_app.create_session(user_id=USER_ID)
    session_id = session.get("id")

    # Pre-warm: First query is slower (cache miss)
    prewarm_start = time.perf_counter()
    async for _ in remote_app.async_stream_query(
        user_id=USER_ID,
        session_id=session_id,
        message=PREWARM_QUERY,
    ):
        pass
    prewarm_time = (time.perf_counter() - prewarm_start) * 1000
    print(f"Pre-warm latency: {prewarm_time:.0f}ms")

    # Subsequent queries benefit from cached instructions
    query_start = time.perf_counter()
    async for _ in remote_app.async_stream_query(
        user_id=USER_ID,
        session_id=session_id,
        message="What did I buy in 2024?",
    ):
        pass
    query_time = (time.perf_counter() - query_start) * 1000
    print(f"Query latency: {query_time:.0f}ms")

    # Expect: query_time < prewarm_time (by ~20-30%)
```

### Latency Measurement Best Practices

```python
"""Accurate latency measurement for async streaming."""

import time

async def measure_query_latency(remote_app, session_id: str, query: str) -> dict:
    """Measure query latency with detailed breakdown."""

    # Use perf_counter for high-resolution timing
    start_time = time.perf_counter()

    events = []
    first_event_time = None

    async for event in remote_app.async_stream_query(
        user_id=USER_ID,
        session_id=session_id,
        message=query,
    ):
        if first_event_time is None:
            first_event_time = time.perf_counter()
        events.append(event)

    end_time = time.perf_counter()

    return {
        "total_ms": (end_time - start_time) * 1000,
        "time_to_first_event_ms": (first_event_time - start_time) * 1000 if first_event_time else None,
        "streaming_duration_ms": (end_time - first_event_time) * 1000 if first_event_time else None,
        "event_count": len(events),
    }
```

---

## Testing RLS (Row Level Security)

### Multi-User Isolation Tests

```python
"""Test that users only see their own data."""

import pytest

USER_A_ID = "user-a-uuid"
USER_B_ID = "user-b-uuid"

@pytest.mark.asyncio
async def test_rls_isolation():
    """Verify users cannot see each other's data."""
    remote_app = agent_engines.get(RESOURCE_NAME)

    # Create sessions for two users
    session_a = remote_app.create_session(user_id=USER_A_ID)
    session_b = remote_app.create_session(user_id=USER_B_ID)

    # Query as User A
    events_a = []
    async for event in remote_app.async_stream_query(
        user_id=USER_A_ID,
        session_id=session_a.get("id"),
        message="Show all my receipts",
    ):
        events_a.append(event)
    response_a = extract_final_response(events_a)

    # Query as User B
    events_b = []
    async for event in remote_app.async_stream_query(
        user_id=USER_B_ID,
        session_id=session_b.get("id"),
        message="Show all my receipts",
    ):
        events_b.append(event)
    response_b = extract_final_response(events_b)

    # Responses should be different (different users' data)
    # Or both should indicate no data if test users have no receipts
    assert response_a != response_b or "no receipts" in response_a.lower()


@pytest.mark.asyncio
async def test_user_id_in_state():
    """Verify user_id is properly set in session state."""
    remote_app = agent_engines.get(RESOURCE_NAME)
    session = remote_app.create_session(user_id=USER_A_ID)

    # The before_agent_callback should validate user_id
    # If it fails, the agent will raise an error
    events = []
    async for event in remote_app.async_stream_query(
        user_id=USER_A_ID,
        session_id=session.get("id"),
        message="What is my user ID?",
    ):
        events.append(event)

    response = extract_final_response(events)
    # Agent should not reveal user_id, but should not error
    assert "error" not in response.lower()
```

---

## Best Practices

1. **Test in isolation**: Unit test tools and agents separately
2. **Mock external calls**: Don't hit real APIs in unit tests
3. **Use fixtures**: Share setup code via conftest.py
4. **Test state flow**: Verify data passes correctly between agents
5. **Parametrize tests**: Test multiple scenarios efficiently
6. **Separate concerns**: Unit vs integration vs evaluation tests
7. **Test edge cases**: Empty inputs, errors, timeouts
8. **Pre-warm deployed agents**: Reduces latency by 20-30%
9. **Use perf_counter**: High-resolution timing for latency measurement
10. **Test RLS isolation**: Verify users only see their own data

---

## Common Pitfalls

1. **Testing exact LLM output**: LLM outputs are non-deterministic
2. **No mocking**: Hitting real APIs makes tests slow and flaky
3. **Missing async**: Forgetting pytest-asyncio for async tests
4. **Stateful tests**: Tests depending on order or shared state
5. **No fixtures**: Duplicating setup code
6. **Wrong event structure**: Events have nested structure: `event['content']['parts'][0]['text']`
7. **Ignoring pre-warm**: First query is slower due to cache miss
8. **Using time.time()**: Use `time.perf_counter()` for accurate latency

---

## Success Criteria

- Unit tests for all custom tools
- Integration tests for agent workflows
- State flow tests for multi-agent systems
- Mocked external dependencies
- Evaluation tests for quality metrics
- CI/CD integration configured
- **Deployed agent tests with async streaming**
- **Benchmark tests with latency statistics**
- **Pre-warming pattern implemented**
- **RLS isolation tests for multi-user scenarios**
