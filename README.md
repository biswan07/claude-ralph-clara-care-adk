# ClaraCare - Intelligent Warranty Claim Agent

ClaraCare is an AI-powered warranty claim processing system for **Smart Receipts** that automatically finds manufacturer support contacts, assesses confidence, and either auto-submits claims or routes them to human review.

## The Problem

When users want to file warranty claims through Smart Receipts, finding the correct manufacturer support email is challenging:
- Support contact information is scattered across manufacturer websites
- Contact details change frequently
- AI systems can "hallucinate" fake email addresses, misleading users
- Manual research is time-consuming and error-prone

## The Solution

ClaraCare is a multi-agent system that:

1. **Searches** internal database AND the web simultaneously for support contacts
2. **Validates** found emails (format, domain, brand match)
3. **Assesses confidence** using multiple signals
4. **Routes intelligently**:
   - **High confidence (≥80%)**: Auto-submit the claim
   - **Low confidence (<80%)**: Queue for human review
   - **No email found**: Escalate to support specialist

**Key Guarantee**: ClaraCare **never fabricates** email addresses. If confidence is low or no email is found, the claim is safely queued for human verification.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER SUBMITS WARRANTY CLAIM                       │
│                     via Smart Receipts App                          │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CLARACARE ORCHESTRATOR                           │
│              Get claim details → Coordinate workflow                │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PARALLEL SEARCH                                   │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   Internal DB Search    │    │     Web Search          │        │
│  │   (Known contacts in    │    │     (Google Search +    │        │
│  │    Supabase)            │    │      Email extraction)  │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      JUDGE AGENT                                     │
│   Evaluate: source reliability, email validity, domain match,       │
│   multiple source agreement → Confidence Score (0-100%)             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┬──────────────┐
                    ▼                           ▼              ▼
          ┌─────────────────┐        ┌─────────────────┐ ┌────────────┐
          │ HIGH CONFIDENCE │        │ LOW CONFIDENCE  │ │ NO EMAIL   │
          │     ≥ 80%       │        │     < 80%       │ │   FOUND    │
          │                 │        │                 │ │            │
          │ Writer Agent    │        │ Queue for Human │ │ Escalate   │
          │ → Compose email │        │ Review          │ │ to Support │
          │ → SUBMITTED     │        │ → PENDING       │ │ → REQUIRES │
          │                 │        │                 │ │   _REVIEW  │
          └─────────────────┘        └─────────────────┘ └────────────┘
```

---

## User Experience

### Auto-Submitted Claim (High Confidence)

```
✓ CLAIM SUBMITTED SUCCESSFULLY

Your warranty claim CLM-001 has been submitted to Sony support.

EMAIL DETAILS
─────────────
To: support@sony.com
Subject: Warranty Claim - Sony WH-1000XM5 Headphones

Dear Sony Support Team,
I am writing to request warranty service for my Sony WH-1000XM5...

CONFIDENCE METRICS
──────────────────
Confidence Score: 92% (Threshold: 80%)
Decision: AUTO_SUBMIT
Reasoning: Email found in internal database and confirmed via web search

NEXT STEPS
──────────
- Your claim email has been queued for delivery
- Expected response time: 3-5 business days
```

### Queued for Review (Low Confidence)

```
⚠ CLAIM QUEUED FOR REVIEW

Your warranty claim CLM-002 requires additional verification.

VERIFICATION STATUS
───────────────────
Confidence Score: 65% (Below threshold: 80%)
Decision: HUMAN_REVIEW
Reason: Email found via web search but domain doesn't match brand

WHAT HAPPENS NEXT
─────────────────
- Our support team will verify the contact information
- Expected response time: 24-48 hours
```

### Escalated (No Email Found)

```
⚠ SUPPORT CONTACT NOT FOUND

Your warranty claim CLM-003 requires specialist assistance.

SEARCH RESULTS
──────────────
Brand: Obscure Electronics
Internal Database: No matching support contact found
Web Search: No valid support email discovered

WHAT HAPPENS NEXT
─────────────────
- Your claim has been escalated to a support specialist
- Our team will research alternative contact methods
- Expected response time: 24-48 hours
```

---

## Architecture

### Agents

| Agent | Purpose |
|-------|---------|
| **Root Orchestrator** | Coordinates entire workflow, manages claim status |
| **DB Search Agent** | Queries Supabase for known support contacts |
| **Web Search Agent** | Searches Google, extracts and validates emails |
| **Judge Agent** | Assesses confidence, makes routing decision |
| **Writer Agent** | Composes professional warranty claim emails |

### Tools

| Tool | Purpose |
|------|---------|
| `search_support_contacts` | Query internal database by brand/category |
| `search_support_email` | Web search for manufacturer support |
| `validate_email` | Check format, DNS, domain match, suspicious patterns |
| `update_claim_status` | Update claim status with full audit trail |
| `get_claim_details` | Retrieve claim information for processing |

### Database Schema

```sql
-- Known support contacts (grows over time)
support_contacts (brand_name, support_email, support_phone, confidence_score)

-- Warranty claims with full status tracking
warranty_claims (user_id, brand_name, status, support_email_used,
                 confidence_score, judge_reasoning, composed_email)

-- Audit trail for all status changes
claim_status_history (claim_id, old_status, new_status, reason, changed_by)
```

---

## Quick Start

### 1. Setup Environment

```bash
cd apps/clara-care

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

Required environment variables:

```bash
# Supabase (for database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-...

# Google Cloud (for ADK)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_GENAI_USE_VERTEXAI=1

# Configuration
CONFIDENCE_THRESHOLD=0.80
MODEL_NAME=gemini-2.5-flash
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Run Locally

```bash
# Web UI at localhost:8000
uv run adk web

# Terminal mode
uv run adk run clara_care
```

### 4. Run Tests

```bash
uv run pytest
```

### 5. Deploy to Production

```bash
uv run python scripts/deploy_to_agent_engine.py
```

---

## Project Structure

```
apps/clara-care/
├── clara_care/
│   ├── __init__.py              # Exports root_agent
│   ├── agent.py                 # Root orchestrator
│   ├── config.py                # Environment configuration
│   ├── supabase_client.py       # Database client
│   │
│   ├── tools/
│   │   ├── db_search.py         # Internal DB search
│   │   ├── web_search.py        # Web search + extraction
│   │   ├── email_validator.py   # Email validation
│   │   └── claim_status.py      # Status management
│   │
│   └── sub_agents/
│       ├── db_search_agent/     # DB specialist
│       ├── web_search_agent/    # Web specialist
│       ├── judge_agent/         # Confidence assessment
│       ├── writer_agent/        # Email composition
│       ├── search_pipeline/     # Parallel search
│       └── search_judge_pipeline/ # Sequential pipeline
│
├── scripts/
│   ├── deploy_to_agent_engine.py  # Production deployment
│   └── test_deployed_agent.py     # Test deployed agent
│
├── tests/
│   ├── unit/test_tools.py         # Tool unit tests
│   └── integration/test_workflow.py # Full workflow tests
│
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `CONFIDENCE_THRESHOLD` | 0.80 | Minimum confidence for auto-submit |
| `MODEL_NAME` | gemini-2.5-flash | LLM model for agents |
| `EMBEDDING_MODEL` | text-embedding-3-small | OpenAI embedding model |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Email accuracy rate | ≥95% |
| Auto-submission rate | ≥80% of claims |
| Human review queue | ≤20% of claims |
| False positive rate | <2% |
| Processing time | <10 seconds |

---

## Development

```bash
# Type check
uv run mypy clara_care

# Lint
uv run ruff check clara_care

# Format
uv run ruff format clara_care

# Run all tests
uv run pytest -v
```

---

## Built With

- **[Google ADK](https://google.github.io/adk-docs/)** - Agent Development Kit
- **[Gemini](https://ai.google.dev/)** - LLM for agent reasoning
- **[Supabase](https://supabase.com/)** - Database and authentication
- **[Claude Code](https://github.com/anthropics/claude-code)** - Development assistance

---

## License

MIT
