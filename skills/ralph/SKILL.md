# PRD to JSON Converter Skill

**Name:** ralph
**Description:** Convert PRDs to prd.json format for the Claude Ralph autonomous agent system.

**Triggers:** convert this prd, turn this into ralph format, create prd.json from this, ralph json, convert to ralph, make prd.json

---

## Instructions

This skill transforms an existing Product Requirements Document (PRD) into the structured JSON format that Claude Ralph uses for autonomous execution.

### Step 1: Locate the PRD

- If user specifies a file, read that file
- Otherwise, look for PRD files in:
  - `tasks/prd-*.md`
  - `docs/prd-*.md`
  - `*.prd.md`
  - Root directory markdown files

### Step 2: Analyze and Convert

Extract the following from the PRD:

1. **Project name** - From title or filename
2. **Branch name** - Suggest format: `claude-ralph/[feature-name]`
3. **Description** - From overview section
4. **User stories** - Convert each to JSON format

### Step 3: Story Sizing (CRITICAL)

**Right-sized stories** complete in ONE Claude Ralph iteration without context loss:
- Add a database column with migration
- Create a single UI component
- Implement one API endpoint
- Add a specific piece of business logic

**Oversized stories** need splitting:
- "Build entire dashboard" → Split into individual widgets
- "Implement full authentication" → Split into register, login, password reset
- "Create admin panel" → Split into individual admin features

If you find oversized stories, split them into smaller, independent pieces.

### Step 4: Acceptance Criteria Standards

Every criterion must be **verifiable**, not vague:

**Good criteria:**
- "Add status column with default 'pending'"
- "Filter dropdown shows: All, Active, Completed"
- "API returns 401 for unauthenticated requests"
- "Typecheck passes"

**Bad criteria:**
- "Works correctly"
- "Is user-friendly"
- "Performs well"

**Required criteria for ALL stories:**
- "Typecheck passes" (or equivalent for the language)

**Required for UI stories:**
- "Verify in browser: [specific visual check]"

### Step 5: Ordering

Stories execute sequentially by priority number. Ensure:
- Dependencies come before dependents
- Schema changes before code that uses them
- Backend before frontend that calls it

---

## Output Format

Create `prd.json` with this structure:

```json
{
  "project": "ProjectName",
  "branchName": "claude-ralph/feature-name",
  "description": "Brief description of the feature",
  "userStories": [
    {
      "id": "US-001",
      "title": "Short descriptive title",
      "description": "As a [role], I want [feature] so that [benefit].",
      "acceptanceCriteria": [
        "Specific criterion 1",
        "Specific criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## Pre-Save Checklist

Before saving `prd.json`, verify:

1. **Story Independence**: Can each story be completed without the others (except explicit dependencies)?
2. **Story Size**: Is each story small enough for a single iteration?
3. **Criteria Verifiability**: Is each acceptance criterion testable?
4. **Proper Ordering**: Are dependencies ordered correctly by priority?
5. **Branch Name**: Is it a valid git branch name?
6. **All passes: false**: Every story should start as incomplete

---

## Output Location

Save the file as `prd.json` in the project root (same directory as `claude-ralph.sh`).

---

## Archive Previous Run

If `prd.json` already exists with a different branch name, remind the user to:
1. Complete or archive the current run first
2. Or manually archive to `archive/YYYY-MM-DD-feature-name/`

---

## Example Transformation

**Input (from PRD):**
```markdown
**US-001: User Registration**
As a new user, I want to create an account so that I can access the application.

Acceptance Criteria:
- [ ] Registration form with email and password fields
- [ ] Email validation
- [ ] Password requirements enforced
```

**Output (to prd.json):**
```json
{
  "id": "US-001",
  "title": "User Registration",
  "description": "As a new user, I want to create an account so that I can access the application.",
  "acceptanceCriteria": [
    "Registration form with email and password fields",
    "Email validation (format check and uniqueness)",
    "Password requires: 8+ chars, 1 uppercase, 1 number",
    "Typecheck passes",
    "Verify in browser: form displays and submits correctly"
  ],
  "priority": 1,
  "passes": false,
  "notes": "First story - no dependencies"
}
```

Note how vague criteria were made specific and required checks were added.
