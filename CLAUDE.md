# Claude Ralph - Project Instructions

This is the Claude Ralph autonomous agent system. When working in this repository, follow these guidelines.

## Project Overview

Claude Ralph is a bash-based autonomous loop that spawns Claude CLI instances to implement PRD user stories iteratively. Each iteration is independent with fresh context.

## File Purposes

- `claude-ralph.sh` - Main loop script, spawns Claude instances
- `prompt.md` - Instructions given to each Claude instance
- `prd.json` - Current PRD with story completion status
- `progress.txt` - Append-only log of learnings across iterations
- `skills/` - Skill definitions for PRD generation and conversion

## Key Patterns

### Completion Signal

When all stories are complete, output exactly: `RALPH_COMPLETE`

This triggers the loop to exit successfully.

### Story Selection

Always select the highest-priority (lowest `priority` number) story where `passes: false`.

### Quality Gates

Before any commit:
1. Run typecheck
2. Run tests
3. Run lint

Never commit failing code.

### Progress Logging

After each story, append to `progress.txt`:
```
---
## [Date] - [Story ID]: [Title]

### What was implemented
- [Changes]

### Learnings for future iterations
- [Patterns discovered]
```

## Editing Guidelines

When modifying this project:

1. **Shell scripts**: Keep POSIX-compatible where possible. Use `shellcheck` for validation.

2. **Markdown files**: Follow consistent heading structure. Skills use specific trigger keywords.

3. **JSON format**: Maintain the exact prd.json schema - the loop depends on `passes`, `priority`, etc.

## Testing Changes

To test modifications:
1. Create a sample `prd.json` with 2-3 simple stories
2. Run `./claude-ralph.sh 3` to test a few iterations
3. Verify stories complete and loop exits properly
