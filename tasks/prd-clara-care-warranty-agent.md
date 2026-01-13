# PRD: ClaraCare Warranty Claim Agent

## Overview

ClaraCare is a multi-agent warranty claim system built on Google ADK that replaces the existing n8n workflow. The system intelligently routes warranty claims by searching internal databases and web sources, assessing confidence levels, and either auto-submitting high-confidence claims or routing low-confidence cases to human reviewers. This eliminates the critical issue of hallucinated email addresses that currently misleads users.

## Goals

- Eliminate hallucinated/fake support email addresses from the system
- Achieve 80%+ accuracy on auto-submitted warranty claims
- Reduce human review queue to only genuinely uncertain cases (<20% of claims)
- Provide clear status visibility to users (Submitted, Pending, Failed)
- Enable human operators to efficiently review and resolve pending claims
- Deploy as a production-ready service on Vertex AI Agent Engine

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ClaraCare Orchestrator                          │
│                        (LlmAgent)                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Search Pipeline                                   │
│                   (SequentialAgent)                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Parallel Search                                 │   │
│  │             (ParallelAgent)                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │   │
│  │  │ Internal DB     │  │ Web Search      │                   │   │
│  │  │ Search Agent    │  │ Agent           │                   │   │
│  │  │ (Supabase)      │  │ (Google Search) │                   │   │
│  │  └─────────────────┘  └─────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Judge Agent                               │   │
│  │              (Confidence Assessment)                         │   │
│  │         Evaluates: source reliability, email validity,       │   │
│  │         domain match, multiple source agreement              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
        ┌───────────────────┐   ┌───────────────────┐
        │ HIGH CONFIDENCE   │   │ LOW CONFIDENCE    │
        │ (≥80%)            │   │ (<80%)            │
        │                   │   │                   │
        │ Writer Agent      │   │ Queue for Human   │
        │ → Send Email      │   │ Review            │
        │ → Status:Submitted│   │ → Status: Pending │
        └───────────────────┘   └───────────────────┘
```

## User Stories

### Phase 1: Core Infrastructure

**US-001: Project Setup and Configuration**
As a developer, I want to set up the ADK project structure so that I have a solid foundation for building the ClaraCare agent.

Acceptance Criteria:
- [ ] Create `apps/clara-care/` directory with standard ADK structure
- [ ] Create `clara_care/` Python package with `__init__.py`, `agent.py`, `config.py`
- [ ] Create `tools/` subdirectory for custom tools
- [ ] Create `sub_agents/` subdirectory for specialist agents
- [ ] Set up `pyproject.toml` with all required dependencies (google-adk, google-genai, supabase, openai, pydantic-settings)
- [ ] Create `.env.example` with all required environment variables
- [ ] Typecheck passes

**US-002: Configuration Management**
As a developer, I want a centralized configuration system so that environment-specific settings are managed properly.

Acceptance Criteria:
- [ ] Create `config.py` using pydantic-settings BaseSettings
- [ ] Support environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, GOOGLE_CLOUD_PROJECT
- [ ] Include model configuration (default: gemini-2.5-flash)
- [ ] Include confidence threshold setting (default: 0.80)
- [ ] Include embedding configuration for vector search
- [ ] Fail-fast validation for required settings
- [ ] Typecheck passes

---

### Phase 2: Database Tools

**US-003: Supabase Client Setup**
As a developer, I want a Supabase client module so that agents can interact with the database.

Acceptance Criteria:
- [ ] Create `supabase_client.py` with client initialization
- [ ] Use service role key for backend operations
- [ ] Export singleton client instance
- [ ] Handle connection errors gracefully
- [ ] Typecheck passes

**US-004: Internal Database Search Tool**
As the search agent, I want to query the internal support contacts database so that I can find known support emails quickly.

Acceptance Criteria:
- [ ] Create `tools/db_search.py` with `search_support_contacts` function
- [ ] Search by brand name (case-insensitive, partial match)
- [ ] Search by product category
- [ ] Return: brand_name, support_email, support_phone, support_url, confidence_score, source
- [ ] Include `ToolContext` as last parameter for user_id access
- [ ] Return JSON string with results or "not found" message
- [ ] Typecheck passes

**US-005: Claim Status Management Tool**
As the system, I want to update warranty claim statuses so that users and operators can track claim progress.

Acceptance Criteria:
- [ ] Create `tools/claim_status.py` with `update_claim_status` function
- [ ] Support statuses: PENDING, SUBMITTED, FAILED, REQUIRES_REVIEW
- [ ] Store: claim_id, status, support_email_used, confidence_score, judge_reasoning, updated_at
- [ ] Create `get_claim_status` function for status retrieval
- [ ] Include audit trail (status history)
- [ ] Typecheck passes

---

### Phase 3: Web Search Tools

**US-006: Web Search Tool for Support Contacts**
As the search agent, I want to search the web for manufacturer support contacts so that I can find emails not in the internal database.

Acceptance Criteria:
- [ ] Create `tools/web_search.py` with `search_support_email` function
- [ ] Use Google Search tool from ADK (`google_search`)
- [ ] Construct targeted search queries: "[brand] warranty support email contact"
- [ ] Parse and extract email addresses from search results
- [ ] Validate email format (regex validation)
- [ ] Return: found_emails (list), search_query, source_urls, raw_results
- [ ] Handle no results gracefully
- [ ] Typecheck passes

**US-007: Email Validation Tool**
As the judge agent, I want to validate email addresses so that I can assess their legitimacy.

Acceptance Criteria:
- [ ] Create `tools/email_validator.py` with `validate_email` function
- [ ] Check email format validity (RFC 5322 compliance)
- [ ] Check domain exists (DNS MX record lookup)
- [ ] Check domain matches expected brand (e.g., sony.com for Sony)
- [ ] Flag suspicious patterns (free email providers, numeric domains)
- [ ] Return: is_valid, domain_exists, domain_matches_brand, suspicion_flags, validation_score
- [ ] Typecheck passes

---

### Phase 4: Specialist Agents

**US-008: Internal DB Search Agent**
As the orchestrator, I want a specialist agent for internal database searches so that known contacts are found efficiently.

Acceptance Criteria:
- [ ] Create `sub_agents/db_search_agent/agent.py`
- [ ] LlmAgent with `search_support_contacts` tool
- [ ] Clear instruction for searching internal database first
- [ ] `output_key="internal_search_result"` for state sharing
- [ ] Return structured result: found (bool), email, confidence, source
- [ ] Typecheck passes

**US-009: Web Search Agent**
As the orchestrator, I want a specialist agent for web searches so that external sources are consulted when internal DB fails.

Acceptance Criteria:
- [ ] Create `sub_agents/web_search_agent/agent.py`
- [ ] LlmAgent with `search_support_email` and `validate_email` tools
- [ ] Instruction to search web and validate found emails
- [ ] `output_key="web_search_result"` for state sharing
- [ ] Return: found (bool), emails (list with validation scores), sources
- [ ] Typecheck passes

**US-010: Judge Agent (Confidence Assessment)**
As the orchestrator, I want a judge agent that assesses confidence so that I can decide whether to auto-submit or queue for human review.

Acceptance Criteria:
- [ ] Create `sub_agents/judge_agent/agent.py`
- [ ] LlmAgent that reads `{internal_search_result}` and `{web_search_result}` from state
- [ ] Evaluate confidence based on: source reliability, email validation score, domain match, multiple source agreement
- [ ] `output_key="judge_verdict"` containing: confidence_score (0.0-1.0), recommended_email, reasoning, decision (AUTO_SUBMIT or HUMAN_REVIEW)
- [ ] Include detailed reasoning for audit trail
- [ ] Typecheck passes

**US-011: Writer Agent (Email Composer)**
As the system, I want a writer agent that composes warranty claim emails so that high-confidence claims are submitted automatically.

Acceptance Criteria:
- [ ] Create `sub_agents/writer_agent/agent.py`
- [ ] LlmAgent that reads claim details and judge verdict from state
- [ ] Compose professional warranty claim email with: user details, product info, purchase date, issue description, receipt reference
- [ ] `output_key="composed_email"` with: to_address, subject, body, claim_id
- [ ] Do NOT actually send email (handled by separate service)
- [ ] Typecheck passes

---

### Phase 5: Agent Orchestration

**US-012: Parallel Search Pipeline**
As the orchestrator, I want to search internal DB and web simultaneously so that search results are gathered efficiently.

Acceptance Criteria:
- [ ] Create `sub_agents/search_pipeline/agent.py`
- [ ] ParallelAgent containing db_search_agent and web_search_agent
- [ ] Both agents write to unique output_keys
- [ ] Results available in session state after parallel execution
- [ ] Typecheck passes

**US-013: Search and Judge Sequential Pipeline**
As the orchestrator, I want a sequential pipeline that searches then judges so that confidence is assessed after all sources are consulted.

Acceptance Criteria:
- [ ] Create `sub_agents/search_judge_pipeline/agent.py`
- [ ] SequentialAgent: parallel_search → judge_agent
- [ ] Judge agent receives all search results via state placeholders
- [ ] Pipeline outputs final verdict with confidence score
- [ ] Typecheck passes

**US-014: Root Orchestrator Agent**
As the system, I want a root orchestrator agent so that warranty claims are processed end-to-end.

Acceptance Criteria:
- [ ] Create `agent.py` with root ClaraCare orchestrator
- [ ] LlmAgent that coordinates the entire workflow
- [ ] Tools: `update_claim_status`, `get_claim_details`
- [ ] Sub-agents: search_judge_pipeline, writer_agent
- [ ] Instruction covers: receive claim → search → judge → route (auto-submit or human queue)
- [ ] `before_agent_callback` to validate user_id and claim_id in state
- [ ] Export as `root_agent` in `__init__.py`
- [ ] Typecheck passes

---

### Phase 6: Routing Logic

**US-015: High-Confidence Auto-Submit Flow**
As a user, I want high-confidence claims to be auto-submitted so that I get fast resolution.

Acceptance Criteria:
- [ ] When judge confidence ≥ 0.80, trigger writer_agent
- [ ] Compose email with recommended support address
- [ ] Update claim status to SUBMITTED
- [ ] Store: support_email_used, confidence_score, judge_reasoning
- [ ] Return confirmation to user with email preview
- [ ] Typecheck passes

**US-016: Low-Confidence Human Review Flow**
As a user, I want uncertain claims to be queued for human review so that I'm not misled by incorrect emails.

Acceptance Criteria:
- [ ] When judge confidence < 0.80, do NOT send email
- [ ] Update claim status to PENDING with reason: "Low confidence - requires human verification"
- [ ] Store: attempted_emails, confidence_scores, judge_reasoning
- [ ] Return message to user: "Your claim requires additional verification and has been queued for review"
- [ ] Typecheck passes

**US-017: No Email Found Flow**
As a user, I want to be informed when no support contact can be found so that I know to seek alternative channels.

Acceptance Criteria:
- [ ] When neither internal DB nor web search finds an email, set status to REQUIRES_REVIEW
- [ ] Store search attempts and reasoning
- [ ] Return message: "We could not find support contact information for [brand]. A support specialist will assist you."
- [ ] Typecheck passes

---

### Phase 7: Testing

**US-018: Unit Tests for Tools**
As a developer, I want unit tests for all tools so that tool behavior is verified.

Acceptance Criteria:
- [ ] Create `tests/unit/test_tools.py`
- [ ] Test `search_support_contacts` with mock Supabase responses
- [ ] Test `search_support_email` with mock search results
- [ ] Test `validate_email` with valid/invalid email cases
- [ ] Test `update_claim_status` state transitions
- [ ] Use pytest fixtures for mock ToolContext
- [ ] All tests pass

**US-019: Integration Tests for Agent Pipeline**
As a developer, I want integration tests so that the full agent workflow is verified.

Acceptance Criteria:
- [ ] Create `tests/integration/test_workflow.py`
- [ ] Test high-confidence flow end-to-end (mock data)
- [ ] Test low-confidence flow routes to human review
- [ ] Test no-email-found flow
- [ ] Test state flows correctly between agents
- [ ] Use InMemorySessionService for testing
- [ ] All tests pass

---

### Phase 8: Deployment

**US-020: Deployment Configuration**
As a developer, I want deployment scripts so that the agent can be deployed to Vertex AI Agent Engine.

Acceptance Criteria:
- [ ] Create `scripts/deploy_to_agent_engine.py`
- [ ] Configure environment variables with Secret Manager references
- [ ] Set `GOOGLE_GENAI_USE_VERTEXAI=1` (critical for Agent Engine)
- [ ] Include all dependencies in requirements list
- [ ] Include `clara_care` package in extra_packages
- [ ] Enable Cloud Trace for observability
- [ ] Typecheck passes

**US-021: Deployed Agent Testing Script**
As a developer, I want a test script for the deployed agent so that production behavior can be verified.

Acceptance Criteria:
- [ ] Create `scripts/test_deployed_agent.py`
- [ ] Support async streaming queries
- [ ] Include pre-warming for cache optimization
- [ ] Test with sample warranty claims
- [ ] Report latency statistics
- [ ] Typecheck passes

---

## Functional Requirements

- **FR-001**: System shall search internal Supabase database before web search
- **FR-002**: System shall validate all email addresses before use
- **FR-003**: System shall require ≥80% confidence for auto-submission
- **FR-004**: System shall queue claims with <80% confidence for human review
- **FR-005**: System shall never fabricate or hallucinate email addresses
- **FR-006**: System shall maintain audit trail of all decisions
- **FR-007**: System shall support user_id-based data isolation (RLS)
- **FR-008**: System shall provide clear status feedback to users

## Non-Goals (Out of Scope)

- Actual email sending (handled by separate email service)
- Human review dashboard UI (separate project)
- Direct retailer API integrations (future phase)
- User authentication (handled by Smart Receipts app)
- Receipt image processing (handled by existing system)
- Payment processing for claims

## Technical Considerations

### Database Schema (Supabase)

```sql
-- Support contacts table (internal database)
CREATE TABLE support_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name TEXT NOT NULL,
    support_email TEXT,
    support_phone TEXT,
    support_url TEXT,
    category TEXT,
    confidence_score FLOAT DEFAULT 1.0,
    source TEXT DEFAULT 'manual',
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Warranty claims table
CREATE TABLE warranty_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    receipt_id UUID REFERENCES receipts(id),
    brand_name TEXT NOT NULL,
    product_description TEXT,
    issue_description TEXT,
    status TEXT DEFAULT 'PENDING',
    support_email_used TEXT,
    confidence_score FLOAT,
    judge_reasoning TEXT,
    composed_email JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Claim status history (audit trail)
CREATE TABLE claim_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES warranty_claims(id),
    old_status TEXT,
    new_status TEXT,
    reason TEXT,
    changed_by TEXT DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI (for embeddings if using vector search)
OPENAI_API_KEY=sk-...

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Agent Engine (CRITICAL)
GOOGLE_GENAI_USE_VERTEXAI=1

# Application
CONFIDENCE_THRESHOLD=0.80
DEFAULT_MODEL=gemini-2.5-flash
```

### Key ADK Patterns to Apply

1. **Prompt Caching**: Static instructions FIRST, dynamic content (dates) at END
2. **Session State**: Use `output_key` for agent outputs, `{placeholder}` to read
3. **ToolContext**: Always LAST parameter in tool functions
4. **User Validation**: `before_agent_callback` to ensure user_id is set
5. **Export**: `root_agent` from `__init__.py` for ADK discovery

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Email accuracy rate | ≥95% | Verified submissions vs total auto-submissions |
| Auto-submission rate | ≥80% | Claims auto-submitted vs total claims |
| Human review queue size | ≤20% | Claims pending review vs total claims |
| False positive rate | <2% | Incorrect emails in auto-submissions |
| Average processing time | <10s | End-to-end claim processing latency |
| User satisfaction | ≥4.5/5 | Post-claim survey rating |

## Open Questions

1. **Email Sending**: Which service will handle actual email delivery? (SendGrid, SES, etc.)
2. **Human Review Dashboard**: Separate project or part of existing Smart Receipts admin?
3. **Retry Logic**: How many times should web search retry before giving up?
4. **Rate Limiting**: Any limits on Google Search API usage?
5. **Notification**: Should users be notified when human review completes?
6. **Feedback Loop**: How do we capture human corrections to improve confidence model?

---

## Implementation Order (Priority)

| Priority | Stories | Description |
|----------|---------|-------------|
| 1 | US-001, US-002, US-003 | Project setup and configuration |
| 2 | US-004, US-005 | Database tools |
| 3 | US-006, US-007 | Web search and validation tools |
| 4 | US-008, US-009, US-010, US-011 | Specialist agents |
| 5 | US-012, US-013, US-014 | Agent orchestration |
| 6 | US-015, US-016, US-017 | Routing logic |
| 7 | US-018, US-019 | Testing |
| 8 | US-020, US-021 | Deployment |
