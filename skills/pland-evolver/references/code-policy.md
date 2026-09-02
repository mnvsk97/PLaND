# Code policy

Apply this policy to every generated or modified Python or Bash command step.

## Minimize total expense

Optimize total cost, not only tokens:

- model input and output tokens;
- wall-clock and service latency;
- CPU, memory, storage, and network use;
- paid API, database, queue, and compute charges;
- maintenance and repeated setup work.

Measure before and after under the same conditions. Prefer the simpler implementation when improvements are insignificant.

## Dependencies

Use the Python standard library or shell built-ins when they solve the problem clearly and reliably. Add the smallest maintained dependency only when it materially improves correctness, portability, or resource use.

Every dependency must be declared in `pyproject.toml` and have a license and execution model compatible with the project. Do not add a library, hosted SDK, binary, or service that requires a paid license, subscription, usage plan, or metered account unless the user explicitly authorizes it. A free SDK that calls a paid service counts as a paid dependency path.

Do not place an LLM, embedding, OCR, search, or other metered model call inside a command represented as deterministic. If semantic model behavior is necessary, keep that operation as an English SOP step or explicitly classify it as agentic.

## Efficient implementation

- Read each input only as often as necessary; stream large inputs instead of loading them fully when practical.
- Avoid repeated parsing, subprocess startup, network round trips, and serialization.
- Batch compatible operations when it reduces cost without obscuring step-level evidence.
- Cache only stable, reusable results; key caches by relevant inputs and versions, and define invalidation.
- Bound input sizes, loops, concurrency, retries, timeouts, output sizes, and temporary storage.
- Use explicit data structures and deterministic ordering where output order matters.
- Return machine-readable output when another step consumes the result.
- Fail early with actionable errors and nonzero exit codes; do not silently fall back to expensive work.
- Keep one clear responsibility per script during evolution. Compose adjacent accepted scripts only after measurements support it.

## Network and services

Network calls are allowed only to endpoints permitted by the fixed project policy, including approved VPC services. Construct requests explicitly, use timeouts, cap retries with backoff, and avoid duplicate writes. Inject credentials through the runtime and never write them to source, logs, traces, or generated artifacts.

Prefer an existing approved service over introducing another dependency when it is cheaper and equally reliable. Record destination, operation, expected request count, timeout, retry policy, idempotency behavior, and estimated service cost.

## Safe execution

- Validate paths, arguments, formats, and external responses.
- Prefer argument arrays over shell interpolation; avoid `shell=True` and dynamic code execution.
- Scope filesystem and process access to what the step requires.
- Use temporary files and cleanup predictably.
- Preserve input data unless mutation is an explicit requirement.
- Do not expand permissions or production effects during evolution.

## Acceptance evidence

Before accepting a command step, record:

- original English step and generated artifact;
- input, output, error, dependency, and network contracts;
- focused success, boundary, and failure checks;
- development and validation accuracy;
- tokens, latency, CPU or memory when material, network calls, and estimated total cost;
- comparison with the prior accepted SOP;
- accept or reject decision.

Passing unit checks is necessary but insufficient. Accept only when the complete hybrid agent satisfies the task-quality guardrail and offers a justified accuracy, expense, latency, variance, or reliability improvement.
