# Generation contract

Keep always-on `instructions.md` limited to the agent's role, output expectations, datasource boundary, and instruction hierarchy. Put task procedure in the SOP skill so it loads only when relevant.

The initial SOP is an all-English ordered list of necessary steps. Prefer one direct sentence per step. Write each step as `N. [SNN] instruction <!-- pland:english -->`. Identifiers are stable across wording and later representation changes, are not renumbered merely because steps move, and are never reused after removal. A later split creates new identifiers. Evolution must retain the original English instruction next to, or through one direct reference from, its reference or command form so escape remains unambiguous. Do not add explanations, examples, edge-case catalogs, scripts, subagents, memory, LangGraph, or additional skills unless the requirements make them necessary for the first runnable version.

Use evals only to identify the input/output contract: columns, split counts, input file types, JSON output keys and types, and the known label vocabulary for classification. Do not copy case identifiers, per-case expected values, reasoning, or metadata into the SOP, prompt, references, or datasource files. The generated `data/eval-profile.json` is the reviewable record of this bounded inspection.

Users provide task meaning in natural language rather than implementing an evaluator. Generate or adapt task-local runner and scorer files from that description and its examples, then show the interpreted success contract for confirmation. The runner may return text, structured output, tool traces, or final state. The scorer returns one named primary quality value and may retain supporting task-specific measurements. Keep this task logic outside the general generator and evolver skills.

The generated project may use approved VPC or API services later, but the initial generator must not introduce a paid product, licensed library, subscription, metered model provider, or network dependency that the requirements did not name. Prefer the standard library and the smallest maintained open-source dependency set. Treat a free SDK that calls a paid service as a paid dependency path.

Expose only tools required by the initial workflow. For a local classification-style workflow, skill reads and approved datasource reads are sufficient: disable the default general-purpose subagent and hide write, edit, delete, shell, search, and listing tools. Extra tools increase prompt size and create additional non-deterministic action paths even when the task never needs them.

Use `references/` inside the generated SOP only when substantial details would otherwise inflate `SKILL.md`. Use `scripts/` only after PLaND evaluation evidence supports replacing a natural-language step.

The generator ends after producing the runnable English baseline. It must not label apparently mechanical work safe to compile, generate guards, or create command candidates before development traces exist. Equivalent inputs must produce the same relevant file contents and deterministic SOP/file ordering. Expected outputs, case identifiers, reasoning, and evaluation metadata remain outside the evaluated agent workspace; only the aggregate, answer-free eval profile may enter it.

Do not add caching or parallel execution to the initial natural-language baseline unless the requirements already demand them. Record those as evolution opportunities instead. During later code generation, inspect for stable repeated computations that can use correctly invalidated caches and for two or more independent operations that can use bounded parallelism without changing semantics or result order.
