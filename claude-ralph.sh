#!/bin/bash
# Claude Ralph - Autonomous AI agent loop using Claude CLI
# Runs Claude repeatedly until all PRD items are complete
# Usage: ./claude-ralph.sh [max_iterations]

set -e

MAX_ITERATIONS=${1:-10}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    if ! command -v claude &> /dev/null; then
        echo -e "${RED}Error: Claude CLI is not installed.${NC}"
        echo "Install it from: https://github.com/anthropics/claude-code"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is not installed.${NC}"
        echo "Install it with: brew install jq (macOS) or apt install jq (Linux)"
        exit 1
    fi

    if [ ! -f "$PRD_FILE" ]; then
        echo -e "${RED}Error: prd.json not found at $PRD_FILE${NC}"
        echo "Create one using the PRD skill or copy from prd.json.example"
        exit 1
    fi

    if [ ! -f "$PROMPT_FILE" ]; then
        echo -e "${RED}Error: prompt.md not found at $PROMPT_FILE${NC}"
        exit 1
    fi
}

# Archive previous run if branch changed
archive_previous_run() {
    if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
        CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
        LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

        if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
            DATE=$(date +%Y-%m-%d)
            FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^claude-ralph/||')
            ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

            echo -e "${YELLOW}Archiving previous run: $LAST_BRANCH${NC}"
            mkdir -p "$ARCHIVE_FOLDER"
            [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
            [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
            echo -e "${GREEN}  Archived to: $ARCHIVE_FOLDER${NC}"

            # Reset progress file for new run
            echo "# Claude Ralph Progress Log" > "$PROGRESS_FILE"
            echo "Started: $(date)" >> "$PROGRESS_FILE"
            echo "---" >> "$PROGRESS_FILE"
        fi
    fi
}

# Track current branch
track_branch() {
    if [ -f "$PRD_FILE" ]; then
        CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
        if [ -n "$CURRENT_BRANCH" ]; then
            echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
        fi
    fi
}

# Initialize progress file if needed
init_progress_file() {
    if [ ! -f "$PROGRESS_FILE" ]; then
        echo "# Claude Ralph Progress Log" > "$PROGRESS_FILE"
        echo "Started: $(date)" >> "$PROGRESS_FILE"
        echo "---" >> "$PROGRESS_FILE"
    fi
}

# Check if all stories are complete
check_completion() {
    local incomplete=$(jq '[.userStories[] | select(.passes == false)] | length' "$PRD_FILE" 2>/dev/null || echo "1")
    if [ "$incomplete" -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Display current status
show_status() {
    echo -e "${BLUE}Current PRD Status:${NC}"
    jq -r '.userStories[] | "  [\(if .passes then "✓" else " " end)] \(.id): \(.title)"' "$PRD_FILE" 2>/dev/null || true
    echo ""
}

# Main execution
main() {
    check_prerequisites
    archive_previous_run
    track_branch
    init_progress_file

    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Claude Ralph - Autonomous Agent Loop           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Max iterations: ${YELLOW}$MAX_ITERATIONS${NC}"
    echo ""

    show_status

    # Check if already complete
    if check_completion; then
        echo -e "${GREEN}All stories already complete! Nothing to do.${NC}"
        exit 0
    fi

    for i in $(seq 1 $MAX_ITERATIONS); do
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  Claude Ralph Iteration $i of $MAX_ITERATIONS${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo ""

        # Run Claude with the prompt
        # Using --dangerously-skip-permissions for autonomous operation
        # Pipe the prompt via stdin using -p flag with file content
        PROMPT_CONTENT=$(cat "$PROMPT_FILE")

        OUTPUT=$(claude -p "$PROMPT_CONTENT" --dangerously-skip-permissions 2>&1 | tee /dev/stderr) || true

        # Check for completion signal
        if echo "$OUTPUT" | grep -q "RALPH_COMPLETE"; then
            echo ""
            echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║          Claude Ralph completed all tasks!               ║${NC}"
            echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "Completed at iteration ${YELLOW}$i${NC} of ${YELLOW}$MAX_ITERATIONS${NC}"
            show_status
            exit 0
        fi

        # Also check prd.json directly
        if check_completion; then
            echo ""
            echo -e "${GREEN}All stories marked complete in prd.json!${NC}"
            show_status
            exit 0
        fi

        echo -e "${YELLOW}Iteration $i complete. Continuing...${NC}"
        sleep 2
    done

    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  Claude Ralph reached max iterations without completing  ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Check $PROGRESS_FILE for status."
    show_status
    exit 1
}

main "$@"
