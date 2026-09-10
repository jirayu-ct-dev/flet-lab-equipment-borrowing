---
name: wayfinder
description: Turn a large, uncertain, multi-session effort into a lightweight map of decisions, dependencies, and unresolved fog. Use when the destination is meaningful but the route is not yet clear; do not use for work that fits a normal implementation plan.
---

# Wayfinder

Create a decision map for work that is too uncertain or too large for one ordinary plan. Wayfinding clarifies the route; it does not implement the destination.

## Decide whether a map is warranted

Use a map when several decisions depend on research, prototypes, human judgment, or one another and the effort will likely span sessions. Use a normal plan when the requirements and implementation path are already clear.

Name the **destination** in one or two sentences. The destination is the observable artifact or decision that ends wayfinding, such as an approved architecture, a migration strategy, or a spec ready to implement.

If a brief inspection shows no meaningful fog, stop and use the project's normal planning workflow.

## Storage and authority

Prefer an existing project convention for plans or design notes. Otherwise use one local file at:

```text
.scratch/wayfinding/<short-name>.md
```

Keep the map local-first. Publish or synchronize it to GitHub, GitLab, Jira, Linear, or another tracker only when the user asks or the project explicitly establishes that workflow. External issue creation, assignment, labels, and comments remain external mutations requiring appropriate authority.

## Map structure

Use a single canonical map until a decision accumulates enough evidence to justify its own linked artifact.

```markdown
# <Destination name>

## Destination
<What must be clear or produced before implementation can begin.>

## Constraints
<Standing scope, project rules, and relevant references.>

## Frontier
- [D1] <A precise decision that can be worked now> — open

## Blocked
- [D2] <Decision> — blocked by D1

## Fog
- <An in-scope area that is visible but cannot yet be phrased as a precise decision>

## Decisions
- [D0] <Decision title> — <one-line outcome> ([evidence](link-or-path))

## Out of scope
- <Explicitly excluded work and why>
```

The map is an index. Put detailed research, prototype output, or discussion in a linked artifact and keep only the decision and a short rationale in the map.

## Chart the route

1. Inspect the repository and existing discussion so settled facts are not reopened.
2. Confirm the destination and material constraints.
3. Add precise questions that can be answered now to the **Frontier**.
4. Put known dependent decisions in **Blocked** with explicit edges.
5. Put visible but still unformulated areas in **Fog**. Fog becomes a decision only when its question can be stated precisely.
6. Record consciously excluded work in **Out of scope**.

Choose the lightest way to resolve each frontier decision:

- inspect local code or documentation;
- research authoritative external sources;
- build a throwaway prototype when behavior or appearance must be experienced;
- ask the user or another stakeholder when the answer depends on human preference or domain knowledge.

Do not create speculative downstream work merely to make the map look complete.

## Advance the map

Work one decision at a time unless independent research can safely proceed in parallel.

For each resolved decision:

1. Capture the outcome and evidence under **Decisions**.
2. Move newly unblocked questions to the **Frontier**.
3. Promote newly precise fog into the frontier or blocked list.
4. Remove invalidated questions and record meaningful scope exclusions.
5. Re-check whether the route to the destination is now clear.

Stop wayfinding when the remaining path can be expressed as an ordinary spec or implementation plan. Summarize the destination, decisions, unresolved risks, and recommended next artifact. Do not continue mapping as a substitute for delivery.
