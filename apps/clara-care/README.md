# ClaraCare - Warranty Claim Agent

ClaraCare is a multi-agent AI system built on **Google ADK (Agent Development Kit)** that automates warranty claim processing for Smart Receipts. It intelligently searches for manufacturer support contacts, validates findings, assesses confidence, and routes claims appropriately.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ROOT ORCHESTRATOR                                │
│              clara_care_orchestrator (LlmAgent)                     │
│                                                                      │
│  Tools: get_claim_details                                           │
│  Sub-agents: search_judge_pipeline                                  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  SEARCH_JUDGE_PIPELINE (Sequential)                 │
│                                                                     │
│  1. SEARCH_PIPELINE (Parallel)                                      │
│     - DB_SEARCH_AGENT                                               │
│     - WEB_SEARCH_AGENT                                              │
│                                                                     │
│  2. JUDGE_AGENT                                                     │
│     - Evaluates confidence & routing                                │
│                                                                     │
│  3. WRITER_AGENT                                                    │
│     - Composes professional warranty claim emails                   │
│                                                                     │
│  4. SUBMISSION_AGENT                                                │
│     - Sends emails (if AUTO_SUBMIT)                                 │
│     - Updates DB status (GUARANTEED)                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Details

### Root Orchestrator (`clara_care_orchestrator`)

The main entry point that coordinates the entire workflow:

1. Retrieves claim details using `get_claim_details`
2. Delegates to `search_judge_pipeline` which handles the entire process:
   - Search (Pipeline)
   - Judgment (Judge)
   - Composition (Writer)
   - Submission/Finalization (Submission)
3. Reports result to the user

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

### Submission Agent (`submission_agent`)

Finalizes the claim process.
- **For AUTO_SUBMIT**: Sends the composed email and updates status to `SUBMITTED`.
- **Otherwise**: Updates status to `PENDING` or `REQUIRES_REVIEW`.
- Ensures DB status is always updated before the flow ends.

---

## Tools

| Tool | File | Purpose |
|------|------|---------|
| `get_claim_details` | `tools/claim_status.py` | Retrieve claim information |
| `update_claim_status` | `tools/claim_status.py` | Update claim status with audit trail |
| `search_support_contacts` | `tools/db_search.py` | Query internal DB by brand/category |
| `search_support_email` | `tools/web_search.py` | Web search for manufacturer support |
| `validate_email` | `tools/email_validator.py` | Validate email format, DNS, domain match |
| `send_email` | `tools/email_tool.py` | Send emails via SMTP (gmail, etc) |

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
    ├── submission_agent/    # Final status update & email sending
    ├── search_pipeline/     # Parallel search (DB + Web)
    └── search_judge_pipeline/ # Sequential: search -> judge -> write -> submit
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

# SMTP Configuration (Required for sending emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
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
    composed_email TEXT,
    attempted_emails TEXT,
    pending_reason TEXT
)

-- Audit trail for all status changes
claim_status_history (
    claim_id UUID,
    old_status TEXT,
    new_status TEXT,
    reason TEXT,
    changed_by TEXT,
    created_at TIMESTAMP,
    support_email_used TEXT,
    confidence_score FLOAT,
    judge_reasoning TEXT,
    attempted_emails TEXT,
    pending_reason TEXT,
    created_by TEXT
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

### 1. Prerequisites: Secret Manager

ClaraCare requires secrets to be stored in Google Secret Manager for security. Run the following commands (replace placeholders with your actual values):

```bash
# Set your project
gcloud config set project your-project-id

# Create secrets
echo -n "https://your-project.supabase.co" | gcloud secrets create SUPABASE_URL --data-file=-
echo -n "your-service-role-key" | gcloud secrets create SUPABASE_SERVICE_ROLE_KEY --data-file=-
echo -n "sk-your-openai-key" | gcloud secrets create OPENAI_API_KEY --data-file=-

# SMTP Configuration (Required for sending emails)
echo -n "smtp.gmail.com" | gcloud secrets create SMTP_HOST --data-file=-
echo -n "587" | gcloud secrets create SMTP_PORT --data-file=-
echo -n "your-email@gmail.com" | gcloud secrets create SMTP_USERNAME --data-file=-
echo -n "your-email@gmail.com" | gcloud secrets create SMTP_FROM_EMAIL --data-file=-
echo -n "your-app-password" | gcloud secrets create SMTP_PASSWORD --data-file=-

# Grant access to Compute Engine service account
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 2. Deploy to Vertex AI Agent Engine

Run the deployment script, specifying your project ID:

```bash
uv run python scripts/deploy_to_agent_engine.py --project smart-receipts-anz
```

This script will:
1. Initialize Vertex AI with the specified project and location (us-central1).
2. Gather all requirements and dependencies.
3. Prepare the agent code (`clara_care`).
4. securely pass Secret Manager references (`projects/...`) as environment variables.
5. Deploy the agent to Vertex AI Agent Engine.

### 3. Test Deployed Agent

Use the provided script to test the deployed agent. You can pass the Resource ID returned from the deployment step, or rely on the default if it matches your latest deployment.

**Note:** Ensure you are authenticated with the correct project to avoid `403 Permission Denied` errors.

```bash
# Test with the specific resource ID (Replace with your actual ID from deployment output)
uv run python scripts/test_deployed_agent.py projects/73252715699/locations/us-central1/reasoningEngines/1304798145263173632

# Or just run it (defaults to the latest successful deployment ID in the script):
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
