---
name: testing-standards
description: Design, write, or review automated tests and test-first changes using stable behavioral seams, proportionate coverage, and disciplined mocking. Use for test strategy, regression tests, TDD, integration tests, or unreliable test suites.
---

# Testing Standards

Use tests to protect observable behavior with the least coupling and maintenance cost. Adapt to the project's existing framework, commands, and conventions.

## Choose the right seam

A seam is a stable public boundary where behavior can be exercised and observed. Prefer the highest practical seam that is deterministic, reasonably fast, and specific enough to diagnose failures.

- Use unit tests for isolated logic with a meaningful public interface.
- Use integration tests for behavior that depends on several real modules or infrastructure boundaries.
- Use end-to-end tests for a small number of critical user journeys that lower layers cannot represent faithfully.
- Avoid testing private methods, internal call order, or incidental implementation structure.

Infer obvious seams from the codebase. Ask the user only when different seam choices would materially change cost, confidence, or architecture.

## Write durable tests

- Name the capability or behavior, not the implementation technique.
- Arrange only the state needed to expose that behavior.
- Derive expected results from the specification, a worked example, or another independent source of truth—not by repeating the implementation's algorithm.
- Assert the smallest complete observable outcome. Multiple assertions are fine when together they describe one behavior.
- Cover realistic success, failure, boundary, and permission states in proportion to risk.
- Control time, randomness, network, and shared state when they would make the result nondeterministic.

A test should fail when the protected behavior breaks and survive an internal refactor that preserves it.

## Mock at real boundaries

Prefer real code for collaborators owned by the project. Use fakes, stubs, or mocks at boundaries such as third-party APIs, clocks, randomness, filesystems, queues, or databases when using the real dependency would be unsafe, slow, or nondeterministic.

- Mock the narrow operation the system consumes, not a generic transport with conditional behavior.
- Return realistic shapes and error modes.
- Do not assert internal call counts unless ordering or cardinality is part of the external contract.
- Prefer a test database or representative adapter when persistence behavior is the subject of the test.

## Test-first workflow

When the user requests TDD or a failing regression test is practical:

1. **Red:** write one behavioral test and run it to confirm the intended failure.
2. **Green:** implement only what is needed for that behavior to pass.
3. **Refactor:** improve the code and test without changing behavior; keep the focused test green.
4. Repeat with the next vertical slice.

Do not write a large imagined test suite before learning from the first working slice. If a test cannot go red because the behavior already exists, state that and verify its sensitivity another way rather than presenting it as test-first evidence.

## Review and verification

Run the narrowest affected tests first. Then run broader suites, type checks, linting, or end-to-end checks when the change's reach warrants them.

During review, look for:

- tests that pass without traversing the claimed path;
- assertions coupled to internals;
- mocks that hide integration failures;
- flaky global state, timing, or ordering assumptions;
- duplicated cases that add maintenance without new confidence;
- important behavior changed without a suitable regression check.

Report exactly which checks ran and any coverage or environment limitations.
