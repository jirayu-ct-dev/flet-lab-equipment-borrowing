# Logic and State Prototypes

Use this mode when the open question is about state transitions, business rules, data shape, or the interface through which callers drive behavior.

## Pick the smallest useful artifact

Prefer one of these shapes:

- a pure reducer when events transform one explicit state;
- a state machine when legal actions depend on the current state;
- a few pure functions over representative data;
- a small module with a narrow public interface when it genuinely owns state;
- a self-contained interactive HTML file when a non-developer should be able to explore it without installing the project.

Keep the decision logic separate from presentation and transport. The shell may be disposable, while isolated logic can inform the later production design.

## Make behavior inspectable

Include:

1. The question and relevant assumptions.
2. The complete meaningful starting state.
3. Controls or commands for the important actions.
4. A readable state view after every action.
5. A few guided scenarios covering the happy path, an awkward edge case, and an invalid or disallowed action when relevant.
6. A reset to a known state so scenarios can be repeated.

Use domain language in labels and output. Raw JSON may be offered as a secondary debug view, but should not be the only explanation for a non-technical reviewer.

## Boundaries

- Keep persistence in memory unless persistence is the question.
- Do not call live external services when fixtures or stubs can answer the question.
- Do not generalize for hypothetical future cases.
- Do not let DOM or UI handlers become the state model's interface.

The mode is complete when the user can drive the risky scenarios and state what behavior should carry forward into the real implementation.
