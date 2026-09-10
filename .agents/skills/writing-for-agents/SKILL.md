---
name: writing-for-agents
description: Write or revise instructions consumed by coding agents, including SKILL.md, AGENTS.md, workflow docs, and context pointers. Use when agent behavior, invocation, scope, or instruction structure needs to become more reliable.
---

# Writing for Agents

Write instructions that change decisions reliably without loading every task with unnecessary rules.

## Start with the contract

Before editing, identify:

- **Consumer:** which agent or harness reads this document?
- **Trigger:** when should it be loaded or followed?
- **Outcome:** what observable behavior should change?
- **Authority:** what actions does the document permit, and what still requires user direction?

If the desired behavior can be enforced mechanically, prefer a formatter, linter, type checker, test, or CI rule. Document judgment and workflow; do not duplicate configuration the agent can inspect cheaply.

## Put guidance at the right level

- Put broad operating principles in the root `AGENTS.md`.
- Put project- or directory-specific facts in the nearest applicable instructions.
- Put reusable, task-specific workflows in a skill.
- Put substantial branch-specific detail in a referenced file loaded only for that branch.

More specific project instructions may refine general guidance. Do not copy the same rule into several levels unless the repetition prevents a demonstrated failure.

## Design strong pointers

A pointer must say both what the target contains and when to read it. This applies to skill descriptions and links from instruction files.

- Front-load the capability and its trigger.
- Cover distinct branches, not a list of synonyms.
- Keep descriptions narrow enough to avoid unrelated activation.
- Name important exclusions only when they prevent likely misrouting.

Weak: `Frontend guidance.`

Stronger: `Build or review Nuxt pages, forms, dashboards, and data tables using the project's Vue, TypeScript, Tailwind, accessibility, and interaction conventions.`

## Write executable guidance

- Prefer outcomes and decision criteria over a rigid recipe when several approaches are valid.
- Use ordered steps when sequence protects correctness or safety.
- End important steps with a checkable completion condition.
- Phrase the desired behavior positively. Use prohibitions for genuine guardrails and pair them with the safe alternative.
- Preserve the user's scope and authorization. A workflow does not grant permission for external writes, commits, deployments, or destructive actions.
- Use absolute language only for real invariants. Mark preferences and defaults as such.

## Keep context clean

Keep the entrypoint focused on what every run needs. Move mode-specific procedures, schemas, or large examples behind explicit references. Do not create a router or reference file when the main document is already short and linear.

Prune:

- advice the capable agent already follows by default;
- duplicated meanings;
- facts available from nearby code or configuration;
- speculative edge cases with no realistic consequence;
- stale examples and prose that does not affect a decision.

Keep each rule beside its rationale or conditions so future edits do not separate them.

## Validate

After editing:

1. Re-read the description alone and check that it would activate for the intended requests and stay quiet otherwise.
2. Trace at least one realistic request through the instructions.
3. Check for conflicts with applicable `AGENTS.md` files and neighboring skills.
4. For a skill, run the available skill validator.
5. Review the diff for duplicated guidance and accidental scope expansion.

The document is done when another agent can identify when it applies, what outcome it must produce, where its authority ends, and how to tell the work is complete.
