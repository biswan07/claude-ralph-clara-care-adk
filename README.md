# Claude Ralph

An autonomous AI agent loop that runs [Claude CLI](https://github.com/anthropics/claude-code) repeatedly until all PRD items are complete.

Inspired by [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph/) and [snarktank/ralph](https://github.com/snarktank/ralph), adapted for Claude CLI.

## How It Works

Claude Ralph spawns iterative Claude instances that:
1. Read a PRD (`prd.json`) containing user stories
2. Select the highest-priority incomplete story
3. Implement that single story
4. Run quality checks (typecheck, tests, lint)
5. Commit working code
6. Update progress tracking
7. Repeat until all stories pass

Each iteration is a **fresh Claude instance** with clean context. Memory persists through:
- Git commit history
- `progress.txt` (learnings across runs)
- `prd.json` (completion status)
- `CLAUDE.md` (project patterns)

## Prerequisites

- [Claude CLI](https://github.com/anthropics/claude-code) installed and authenticated
- `jq` command-line tool
- Git repository for your project

```bash
# Install jq if needed
brew install jq        # macOS
apt install jq         # Ubuntu/Debian
```

## Quick Start

### 1. Copy to Your Project

```bash
# Clone this repo
git clone https://github.com/YOUR_USERNAME/claude-ralph.git

# Copy files to your project
cp claude-ralph/claude-ralph.sh your-project/scripts/
cp claude-ralph/prompt.md your-project/scripts/
cp claude-ralph/prd.json.example your-project/prd.json
```

### 2. Create Your PRD

Option A: Use the PRD skill (if installed):
```bash
claude "Create a PRD for [your feature]"
```

Option B: Manually create `prd.json` based on the example.

### 3. Convert to JSON Format

If you have a markdown PRD:
```bash
claude "Convert tasks/prd-my-feature.md to ralph format"
```

### 4. Run Claude Ralph

```bash
./scripts/claude-ralph.sh [max_iterations]
```

Default is 10 iterations. The loop exits when:
- All stories have `passes: true`, or
- Max iterations reached

## File Structure

```
your-project/
├── scripts/
│   ├── claude-ralph.sh    # Main loop script
│   └── prompt.md          # Instructions for each Claude instance
├── prd.json               # User stories with pass/fail status
├── progress.txt           # Append-only learnings log
├── CLAUDE.md              # Project-specific Claude instructions
└── archive/               # Archived previous runs
```

## PRD Format

```json
{
  "project": "MyApp",
  "branchName": "claude-ralph/feature-name",
  "description": "Feature description",
  "userStories": [
    {
      "id": "US-001",
      "title": "Story title",
      "description": "As a [role], I want [feature]...",
      "acceptanceCriteria": [
        "Specific criterion 1",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

## Skills

### PRD Generator (`skills/prd/`)

Generates comprehensive Product Requirements Documents through interactive Q&A.

Usage:
```bash
claude "Create a PRD for user authentication"
```

### PRD to JSON Converter (`skills/ralph/`)

Converts markdown PRDs to `prd.json` format for Claude Ralph execution.

Usage:
```bash
claude "Convert this PRD to ralph format"
```

### Installing Skills Globally

Copy skills to your Claude CLI config:

```bash
mkdir -p ~/.claude/commands
cp -r skills/prd ~/.claude/commands/
cp -r skills/ralph ~/.claude/commands/
```

## Critical Concepts

### Fresh Context Per Iteration

Each Claude instance is independent. No conversation history carries over. Memory flows through:
- Git commits from previous work
- `progress.txt` with accumulated learnings
- `prd.json` completion markers

### Small, Focused Tasks

Stories must be completable within one context window:

**Good story sizes:**
- Add a database column
- Create a single UI component
- Implement one API endpoint
- Add a specific validation rule

**Too large (split these up):**
- Build entire dashboard
- Implement full authentication system
- Create complete admin panel

### Quality Feedback Loops

Every iteration runs quality checks. Broken code compounds across iterations, so:
- Typecheck must pass
- Tests must pass
- Lint must pass

### CLAUDE.md Updates

After each iteration, discovered patterns should be added to `CLAUDE.md` files. This helps future iterations understand:
- API conventions
- Non-obvious requirements
- File dependencies
- Testing approaches

## Debugging

Check current state:
```bash
# View story status
cat prd.json | jq '.userStories[] | {id, title, passes}'

# View progress log
cat progress.txt

# View recent commits
git log --oneline -10
```

## Archive

When starting a new feature, Claude Ralph automatically archives the previous run:
```
archive/
└── 2024-01-15-previous-feature/
    ├── prd.json
    └── progress.txt
```

## Differences from Original Ralph

| Original (Amp) | Claude Ralph |
|----------------|--------------|
| `amp --dangerously-allow-all` | `claude -p "..." --dangerously-skip-permissions` |
| `~/.config/amp/skills/` | `~/.claude/commands/` |
| `AGENTS.md` | `CLAUDE.md` |
| `<promise>COMPLETE</promise>` | `RALPH_COMPLETE` |

## License

MIT

## Credits

- Original Ralph pattern by [Geoffrey Huntley](https://ghuntley.com/ralph/)
- Amp implementation by [snarktank](https://github.com/snarktank/ralph)
- Claude CLI by [Anthropic](https://github.com/anthropics/claude-code)
