# ClaraCare - Warranty Claim Agent

ClaraCare is a multi-agent AI system built on **Google ADK (Agent Development Kit)** that automates warranty claim processing for Smart Receipts. It intelligently searches for manufacturer support contacts, validates findings, assesses confidence, and routes claims appropriately.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ROOT ORCHESTRATOR                                │
│              clara_care_orchestrator (LlmAgent)                     │
│                                                                      │
│  Tools: get_claim_details, update_claim_status                      │
│  Sub-agents: search_judge_pipeline, writer_agent                    │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
┌─────────────────────────┐                 ┌─────────────────────────┐
│  SEARCH_JUDGE_PIPELINE  │                 │     WRITER_AGENT        │
│   (SequentialAgent)     │                 │      (LlmAgent)         │
│                         │                 │                         │
│  1. search_pipeline     │                 │  Composes professional  │
│  2. judge_agent         │                 │  warranty claim emails  │
└───────────┬─────────────┘                 └─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SEARCH_PIPELINE                                 │
│                     (ParallelAgent)                                  │
│                                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   DB_SEARCH_AGENT       │    │   WEB_SEARCH_AGENT      │        │
│  │      (LlmAgent)         │    │      (LlmAgent)         │        │
│  │                         │    │                         │        │
│  │  Tools:                 │    │  Tools:                 │        │
│  │  - search_support_      │    │  - search_support_email │        │
│  │    contacts             │    │  - validate_email       │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        JUDGE_AGENT                                   │
│                        (LlmAgent)                                    │
│                                                                      │
│  Evaluates search results and produces:                             │
│  - recommended_email: Best email found (or null)                    │
│  - confidence_score: 0.0 to 1.0                                     │
│  - reasoning: Explanation for the decision                          │
│  - decision: AUTO_SUBMIT | HUMAN_REVIEW | REQUIRES_REVIEW           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Details

### Root Orchestrator (`clara_care_orchestrator`)

The main entry point that coordinates the entire workflow:

1. Retrieves claim details using `get_claim_details`
2. Delegates to `search_judge_pipeline` for contact discovery
3. Routes based on confidence:
   - **>= 80%**: Triggers `writer_agent`, updates status to `SUBMITTED`
   - **< 80%**: Updates status to `PENDING` for human review
   - **No email**: Updates status to `REQUIRES_REVIEW`

### Search Pipeline (`search_pipeline`)

A `ParallelAgent` that runs two searches simultaneously:

- **DB Search Agent**: Queries Supabase for known support contacts
- **Web Search Agent**: Searches the web and validates found emails

### Judge Agent (`judge_agent`)

Evaluates all search results considering:
- Source reliability (internal DB vs web)
- Email format validity
- Domain matching with brand
- Multiple source agreement

### Writer Agent (`writer_agent`)

Composes professional warranty claim emails when confidence is high enough. Reads claim details and judge verdict from session state.

---

## Tools

| Tool | File | Purpose |
|------|------|---------|
| `get_claim_details` | `tools/claim_status.py` | Retrieve claim information |
| `update_claim_status` | `tools/claim_status.py` | Update claim status with audit trail |
| `search_support_contacts` | `tools/db_search.py` | Query internal DB by brand/category |
| `search_support_email` | `tools/web_search.py` | Web search for manufacturer support |
| `validate_email` | `tools/email_validator.py` | Validate email format, DNS, domain match |

---

## Project Structure

```
clara_care/
├── __init__.py              # Exports root_agent
├── agent.py                 # Root orchestrator definition
├── config.py                # Pydantic settings management
├── supabase_client.py       # Database client
│
├── tools/
│   ├── __init__.py
│   ├── claim_status.py      # get_claim_details, update_claim_status
│   ├── db_search.py         # search_support_contacts
│   ├── web_search.py        # search_support_email
│   └── email_validator.py   # validate_email
│
└── sub_agents/
    ├── __init__.py
    ├── db_search_agent/     # Internal DB search specialist
    ├── web_search_agent/    # Web search + validation specialist
    ├── judge_agent/         # Confidence assessment
    ├── writer_agent/        # Email composition
    ├── search_pipeline/     # Parallel search (DB + Web)
    └── search_judge_pipeline/ # Sequential: search -> judge
```

---

## Configuration

Environment variables (set in `.env`):

```bash
# Required - Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Required - OpenAI (for embeddings)
OPENAI_API_KEY=sk-...

# Required - Google Cloud (for ADK)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_GENAI_USE_VERTEXAI=1

# Optional - Defaults shown
CONFIDENCE_THRESHOLD=0.80
MODEL_NAME=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-3-small
```

---

## Quick Start

### 1. Setup Environment

```bash
cd apps/clara-care
cp .env.example .env
# Edit .env with your credentials
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Run the Agent

```bash
# Web UI at localhost:8000
uv run adk web

# Terminal mode
uv run adk run clara_care
```

### 4. Test a Claim

In the ADK web interface or terminal:

```
Process warranty claim CLM-001
```

---

## Routing Logic

The confidence threshold determines claim routing:

| Confidence | Decision | Status | Action |
|------------|----------|--------|--------|
| >= 80% | AUTO_SUBMIT | SUBMITTED | Email composed and queued |
| < 80% | HUMAN_REVIEW | PENDING | Queued for verification |
| No email | REQUIRES_REVIEW | REQUIRES_REVIEW | Escalated to specialist |

---

## Session State Keys

The agents communicate via session state:

| Key | Set By | Description |
|-----|--------|-------------|
| `claim_details` | Root | Full claim information |
| `internal_search_result` | DB Search Agent | Database search results |
| `web_search_result` | Web Search Agent | Web search results |
| `judge_verdict` | Judge Agent | Confidence assessment |
| `composed_email` | Writer Agent | Final email content |

---

## Database Schema

```sql
-- Known support contacts (grows over time)
support_contacts (
    brand_name TEXT,
    support_email TEXT,
    support_phone TEXT,
    confidence_score FLOAT
)

-- Warranty claims with full status tracking
warranty_claims (
    id UUID PRIMARY KEY,
    user_id UUID,
    brand_name TEXT,
    product_name TEXT,
    status TEXT,  -- PENDING, SUBMITTED, FAILED, REQUIRES_REVIEW
    support_email_used TEXT,
    confidence_score FLOAT,
    judge_reasoning TEXT,
    composed_email TEXT
)

-- Audit trail for all status changes
claim_status_history (
    claim_id UUID,
    old_status TEXT,
    new_status TEXT,
    reason TEXT,
    changed_by TEXT,
    created_at TIMESTAMP
)
```

---

## Development

```bash
# Run tests
uv run pytest

# Run specific test
uv run pytest tests/unit/test_tools.py -v

# Type check
uv run mypy clara_care

# Lint
uv run ruff check clara_care

# Format
uv run ruff format clara_care
```

---

## Deployment

### Deploy to Google Agent Engine

```bash
uv run python scripts/deploy_to_agent_engine.py
```

### Test Deployed Agent

```bash
uv run python scripts/test_deployed_agent.py
```

---

## Key Design Decisions

1. **Never Hallucinate Emails**: ClaraCare never fabricates email addresses. Low confidence or no results safely queue for human review.

2. **Parallel Search**: Internal DB and web search run simultaneously for faster results.

3. **Confidence-Based Routing**: Clear threshold (80%) separates auto-submit from human review.

4. **Full Audit Trail**: Every status change is logged with reasoning for compliance.

5. **Prompt Caching**: Static instruction content is placed first for Gemini caching optimization.

---

## Built With

- **[Google ADK](https://google.github.io/adk-docs/)** - Agent Development Kit
- **[Gemini](https://ai.google.dev/)** - LLM for agent reasoning
- **[Supabase](https://supabase.com/)** - Database and authentication
- **[Pydantic](https://docs.pydantic.dev/)** - Configuration validation
