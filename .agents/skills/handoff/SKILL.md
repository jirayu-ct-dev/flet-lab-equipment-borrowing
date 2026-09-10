---
name: handoff
description: Create a compact, redacted handoff document that lets a fresh agent continue the current work. Use only when the user explicitly invokes `$handoff` or asks to prepare context for another agent or session.
---

# Handoff

Write a concise Markdown handoff that captures the current conversation and work state for a fresh agent.

## Workflow

1. Identify the user's goal, completed work, current state, unresolved decisions, blockers, and the next concrete actions.
2. If the user supplied text with the invocation, treat it as the intended focus of the next session and tailor the handoff to it.
3. Inspect relevant workspace state when needed to make the handoff accurate. Do not perform unrelated implementation work.
4. Reference existing PRDs, plans, ADRs, issues, commits, diffs, and other artifacts by path or URL instead of duplicating their contents.
5. Redact secrets, tokens, passwords, private credentials, and personally identifiable information. Never copy `.env` values or other sensitive data.
6. Save the document in the operating system's temporary directory, never in the current workspace. Use a clear filename such as `codex-handoff-YYYYMMDD-HHmm.md` and avoid overwriting an existing file.
7. Return the absolute path to the saved document and a one-sentence summary.

## Document structure

Include only sections that add useful information:

- `# Handoff`
- `## Next-session focus`
- `## Objective`
- `## Current state`
- `## Decisions and constraints`
- `## Relevant artifacts`
- `## Verification performed`
- `## Blockers and risks`
- `## Recommended next steps`
- `## Suggested skills`

In `Suggested skills`, name the available skills the next agent should invoke and briefly state why. Do not invent skills that are not available in the current environment; if availability is uncertain, label the suggestion as conditional.

Keep the document compact and operational. Summarize conclusions rather than reproducing the conversation transcript.
