# Dependency and execution policy

Generated Python projects declare dependencies in `pyproject.toml`.

Prefer maintained open-source libraries that execute locally. A free SDK does not imply a free runtime service, so inspect both dependencies and behavior.

Command steps may call network services when every destination is explicitly permitted by project policy. VPC services and approved APIs are valid deterministic components when request construction and response handling are explicit. Inject credentials at runtime; never store them in the skill.

Do not introduce:

- a paid product or metered service without explicit authorization;
- an LLM call inside a step represented as deterministic;
- undeclared network destinations;
- dependencies that execute install-time downloads or code without review;
- access broader than the source step requires.

Measure total runtime cost, including compute, storage, and service calls. A command is not an improvement merely because it reduces prompt tokens.
