---
name: diagnosing-bugs
description: Diagnose reproducible or intermittent bugs, failures, and performance regressions by building evidence, narrowing causes, and verifying conclusions. Use for debugging and root-cause analysis; implement a fix only when the request includes fixing.
---

# Diagnosing Bugs

Find the cause with the tightest practical evidence loop. Match the depth of the process to the difficulty and risk of the bug.

## Respect the requested outcome

- If the user asks for diagnosis, determine and explain the cause. Do not change behavior unless asked.
- If the user asks to fix the bug, diagnose first, then make the smallest supported change.
- Temporary instrumentation and local repro artifacts are diagnostic tools, not authorization to modify production systems or expose sensitive data.

Redact credentials, tokens, personal data, authentication headers, and sensitive payloads from commands and reported output.

## 1. Establish the symptom

State the expected behavior, actual behavior, affected path, and known conditions. Inspect relevant code, logs, tests, recent changes, and project documentation before forming a conclusion.

Build the narrowest practical signal that can distinguish the bug from success. Prefer, in order of fit:

- an existing or new focused test;
- a repeatable CLI, HTTP, or browser action;
- a minimal fixture or replayed redacted input;
- a targeted measurement or profiler capture for performance;
- a structured human-in-the-loop reproduction when automation is not possible.

Run the signal at least once when the environment permits. If the issue cannot be reproduced, document what was checked and use available evidence without pretending the signal is stronger than it is.

## 2. Narrow the failing path

Reduce inputs, configuration, callers, and steps one at a time while preserving the symptom. Trace the real path from entry point through branches and state changes to the visible failure.

For intermittent failures, improve the reproduction rate through repetition, controlled concurrency, pinned time or randomness, and isolated dependencies. Do not confuse a nearby error with the reported bug.

## 3. Test explanations

When the cause is not obvious, rank a small set of falsifiable hypotheses. For each one, name the observation that would support or reject it. Test the cheapest high-information hypothesis first and change one variable at a time.

Prefer debuggers, focused probes, query plans, and boundary logs over broad logging. Tag temporary instrumentation with a unique marker so it can be removed reliably.

## 4. Conclude or fix

A diagnosis should identify:

- the root cause or the strongest remaining explanation;
- the evidence path that supports it;
- why plausible alternatives were rejected;
- any uncertainty or missing access that limits confidence.

When a fix is authorized:

1. Add a regression check at the highest stable seam that reproduces the behavior, when the project has a suitable test structure.
2. Confirm it fails for the intended reason.
3. Apply the smallest fix supported by the evidence.
4. Re-run the focused signal, then broader relevant checks in proportion to risk.
5. Remove temporary instrumentation and throwaway artifacts that should not remain.

Do not add a shallow or implementation-coupled regression test merely to claim coverage. If no stable seam exists, report that architectural limitation explicitly.

## Handoff

Report the symptom reproduced, root cause, evidence, changes made if any, verification performed, and remaining uncertainty. Never claim reproduction or verification that was not run.
