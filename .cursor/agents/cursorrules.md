# Agent Workflow Rules

**CRITICAL: Follow these steps in order. Do NOT skip any step.**

## Step 1: Select Agent

**Check in this order:**

1. **Explicit mention**: `@code-modifier`, `@code-suggester`, `@qa-agent`, `@default-agent` → Use that agent
2. **User intent analysis**:
   - User wants code **modified/created/changed** (telling you to do it) → `code-modifier`
   - User wants to **test/verify/check** code quality → `qa-agent`
   - User asks **code-related questions/seeks advice** → `code-suggester`
   - **General conversation/info request/unclear** → `default-agent`
3. **Default**: If unclear → `default-agent`

## Step 2: Read Agent File (MANDATORY)

**You MUST read the selected agent file BEFORE doing anything else:**

- `code-modifier` → Read `.cursor/agents/code-modifier.md`
- `code-suggester` → Read `.cursor/agents/code-suggester.md`
- `qa-agent` → Read `.cursor/agents/qa-agent.md`
- `default-agent` → Read `.cursor/agents/default-agent.md`

**Do NOT proceed without reading the agent file.**

## Step 3: Execute Agent Workflow

Follow the workflow defined in the agent file you just read.

---

## Quick Reference

### code-modifier
- **When**: User tells you to modify code (command, not question)
- **Does**: Modifies code using search_replace/write tools
- **Does NOT**: Suggest or test

### code-suggester  
- **When**: User asks for advice/suggestions (question, not command)
- **Does**: Provides suggestions and explanations
- **Does NOT**: Modify code or test

### qa-agent
- **When**: User wants to test/verify/check quality
- **Does**: Runs tests and quality checks
- **Does NOT**: Modify code or suggest

### default-agent
- **When**: General conversation, info requests, or unclear intent
- **Does**: Provides direct answers and explanations
- **Does NOT**: Modify code, suggest, or test

---

**Remember: Only ONE agent runs per request. Each agent is independent.**

---

## Python Commands

**Always use `uv run`. Never use `python3` or `python`.**
