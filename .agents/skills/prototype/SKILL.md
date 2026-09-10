---
name: prototype
description: Build a deliberately temporary prototype to answer one uncertain question about UI, interaction, business logic, or state behavior. Use when a concrete artifact will resolve uncertainty faster than discussion; do not treat prototype code as production-ready implementation.
---

# Prototype

A prototype is a disposable learning artifact. Its success criterion is an answered question, not production-quality code.

## Choose the question and mode

State one question before writing code. Then choose the shape that exposes the uncertainty:

- For state transitions, business rules, data shape, or API ergonomics, read [references/logic.md](references/logic.md).
- For layout, information hierarchy, interaction, or visual direction, read [references/ui.md](references/ui.md).

If both matter, prototype the riskier uncertainty first. Do not build a miniature production application to answer two questions at once.

## Shared constraints

- Mark files and routes clearly as prototypes and keep them close to the relevant project area.
- Follow the existing runtime, routing, component library, and styling system unless a self-contained artifact is materially faster.
- Make the prototype trivial to run and explain the command or URL.
- Use in-memory or stubbed data by default. Do not perform real production mutations or depend on production credentials.
- Implement only the fidelity needed to evaluate the question. Skip abstractions, broad error handling, compatibility work, and tests unless one of them is itself the subject of the experiment.
- Surface the relevant state and assumptions so the user can understand what each action or variation demonstrates.
- Keep accessibility sufficient for evaluation: controls need labels, keyboard operation where relevant, readable contrast, and visible state.

Prototype constraints do not authorize bypassing repository safety rules or modifying unrelated production code.

## Evaluate and conclude

Hand over the runnable artifact with:

- the question it explores;
- how to run it;
- which scenarios or variants to inspect;
- known shortcuts that make it unsuitable for production.

After feedback, record the decision and why it won. Promote the validated idea into production code through the project's normal implementation and testing standards; do not simply relabel the prototype as finished code.

Remove, retain, or archive the prototype only within the user's requested scope. If it remains in the working tree, keep its temporary status unmistakable.
