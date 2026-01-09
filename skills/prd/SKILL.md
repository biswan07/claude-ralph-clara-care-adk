# PRD Generator Skill

**Name:** prd
**Description:** Generate a Product Requirements Document (PRD) for a new feature. Use when planning a feature, starting a new project, or when asked to create a PRD.

**Triggers:** create a prd, write prd for, plan this feature, requirements for, spec out, generate prd

---

## Instructions

When this skill is invoked, follow this two-step process:

### Step 1: Clarifying Questions

Ask 3-5 essential questions to understand the feature requirements. Format questions with lettered options (A, B, C, D) for quick responses.

Focus your questions on:
- **Problem/Goal**: What problem does this solve? What's the primary goal?
- **Core Functionality**: What are the must-have features?
- **Scope Boundaries**: What's explicitly out of scope?
- **Target Users**: Who will use this feature?
- **Success Criteria**: How do we know when it's done?

Example format:
```
1. What is the primary goal of this feature?
   A) Improve user engagement
   B) Reduce operational costs
   C) Add new revenue stream
   D) Fix existing pain point

2. Who is the primary user?
   A) End users/customers
   B) Internal team members
   C) Administrators
   D) Third-party integrators
```

Wait for user responses (e.g., "1A, 2C, 3B") before proceeding.

### Step 2: Generate the PRD

Create a comprehensive PRD with these sections:

#### 1. Introduction/Overview
Brief description of the feature and its purpose (2-3 sentences).

#### 2. Goals
Bulleted list of specific, measurable objectives.

#### 3. User Stories
Format each story as:
```
**US-XXX: [Title]**
As a [role], I want [feature] so that [benefit].

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

Number stories sequentially (US-001, US-002, etc.).

#### 4. Functional Requirements
Numbered list of specific functional requirements (FR-001, FR-002, etc.).

#### 5. Non-Goals
Explicitly state what is OUT of scope to prevent scope creep.

#### 6. Design Considerations (Optional)
UI/UX considerations, wireframe descriptions, or design constraints.

#### 7. Technical Considerations (Optional)
Architecture decisions, API design, database changes, or integration requirements.

#### 8. Success Metrics
How success will be measured (quantitative where possible).

#### 9. Open Questions
Any unresolved questions or decisions needed.

---

## Output Requirements

- **Format:** Markdown (.md)
- **Location:** Save to `tasks/` directory (create if needed)
- **Filename:** `prd-[feature-name].md` (use kebab-case)

Example: `tasks/prd-user-authentication.md`

---

## Critical Rules

1. **Do NOT start implementing** - This skill only creates the PRD document
2. **Be specific** - Vague requirements lead to implementation problems
3. **Size appropriately** - Each user story should be completable in a single development session
4. **Include acceptance criteria** - Every story needs testable criteria
5. **Ask before assuming** - If something is unclear, ask a clarifying question

---

## Example Output

```markdown
# PRD: User Authentication System

## Overview
Implement a secure user authentication system allowing users to register, login, and manage their accounts.

## Goals
- Enable secure user registration and login
- Support password reset functionality
- Implement session management with JWT tokens

## User Stories

**US-001: User Registration**
As a new user, I want to create an account so that I can access the application.

Acceptance Criteria:
- [ ] Registration form with email and password fields
- [ ] Email validation (format and uniqueness)
- [ ] Password strength requirements enforced
- [ ] Confirmation email sent on registration
- [ ] Typecheck passes

**US-002: User Login**
As a registered user, I want to log in so that I can access my account.

Acceptance Criteria:
- [ ] Login form with email and password
- [ ] JWT token generated on successful login
- [ ] Token stored securely in httpOnly cookie
- [ ] Error message for invalid credentials
- [ ] Typecheck passes

[...continued...]
```
