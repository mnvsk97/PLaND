# Path to Least Non-Determinism: Eval-Guided Evolution of Hybrid Agent Skills

**[Author 1]**, **[Author 2]**
*[Affiliations and corresponding-author details to be supplied]*

> **Draft status:** The repository now contains a later frozen-system-prompt
> schema-v2 experiment with an accepted command-bearing hybrid SOP. The results
> below describe the earlier constrained-agent experiment and should be revised
> from `experiments/document-classification/schema-v2/RESULTS.md` before author
> review or submission.

## Abstract

Agent skills package procedural knowledge as natural-language instructions,
references, and executable resources, but a fully language-mediated workflow
can repeatedly spend model tokens on operations that are stable enough to be
constrained or implemented deterministically. This paper introduces Path to
Least Non-Determinism (PLaND), an evaluation-guided method that treats each
standard operating procedure (SOP) step as an optimization unit. A step may
remain an English instruction, move into a focused reference, or become an
explicit executable operation when the behavior is mechanical, testable, and
economically justified. PLaND freezes the model, evaluation truth, scorer,
datasources, and permissions; proposes bounded changes from development traces;
and accepts candidates only after deterministic quality and resource
guardrails. We implemented PLaND as two Agent Skills: one generates a minimal
LangChain DeepAgent and one evaluates and evolves its SOP. In a 20-case OCR-text
document-classification proof-of-concept using local Qwen3-14B, the accepted
agent matched the initial agent's 100% validation accuracy while reducing
aggregate validation tokens from 173,222 to 92,839 (46.40%). Mean validation
latency increased from 11.31 to 12.78 seconds. Three cheaper candidates were
rejected because they reduced accuracy or violated output constraints,
including an attempted deterministic signal extractor. These results show why
the useful objective is not maximal determinism: it is the least non-
determinism that preserves measured task quality under explicit cost and
latency constraints.

**Keywords:** agent skills; agentic workflows; evaluation-driven optimization;
hybrid systems; deterministic execution; large language models; document
classification

## 1. Introduction

Large language model (LLM) agents increasingly solve tasks through compound
workflows: they load procedural instructions, inspect data, call tools, and
iterate until they can return an answer. Agent Skills standardize one practical
form of procedural packaging. A skill contains a required `SKILL.md` and may
bundle scripts, references, and assets; compatible agents progressively load
metadata, instructions, and resources only when needed [1]. This design reduces
always-on context, but it does not by itself decide which parts of a procedure
should consume model reasoning.

Consider a document classifier. The semantic decision between an email, form,
letter, report, or scientific article may require contextual judgment. Reading
an approved file, validating an output schema, counting stable markers, or
restricting irrelevant tools does not necessarily require the same degree of
open-ended inference. If all steps remain English instructions, a model may
reinterpret mechanical operations on every run. If too many steps are compiled
into heuristics, the workflow can become brittle and lose semantic accuracy.

We study the following question:

> Can an agent skill evolve toward more constrained or executable behavior
> while preserving measured task quality and reducing inference expense?

We introduce **Path to Least Non-Determinism (PLaND)**, an eval-guided workflow
for selectively changing the representation of SOP steps. PLaND contributes:

1. a three-representation model for skill steps: English instruction, focused
   reference, or executable command/tool operation;
2. an evolution protocol that freezes evaluation invariants, uses development
   traces to propose bounded changes, and gates acceptance on validation;
3. two reusable Agent Skills, `generate-initial-version` and `pland-evolver`;
4. an end-to-end local experiment showing both accepted and rejected attempts
   to reduce non-determinism; and
5. an explicit multi-objective view of expense covering tokens, latency,
   compute, dependencies, network use, and maintenance.

The central finding is deliberately narrower than “code is better than
instructions.” Code steps bypass unnecessary model reasoning when their
contracts are stable, but attempted compilation can reduce accuracy. In our
experiment, deterministic cue extraction was rejected, while restricting the
available agent actions and refining one semantic precedence rule was accepted.

## 2. Background and Related Work

### 2.1 Agent skills and progressive disclosure

The Agent Skills specification defines a directory containing `SKILL.md` and
optional `scripts/`, `references/`, and `assets/` directories [1]. The format
uses progressive disclosure: agents initially receive skill metadata, load the
full instructions when a task activates the skill, and retrieve other resources
only as required. The specification recommends concise instructions and
one-level relative references. PLaND adopts this packaging model but adds an
evaluation process for deciding how individual SOP steps should be represented.

DeepAgents provides a LangChain-based agent harness with filesystem backends,
tools, subagents, and skills [2]. These facilities make it possible to test not
only prompt text but also the action surface exposed to a model. Our traces show
that irrelevant actions are not neutral: one initial case repeatedly invoked a
write operation 21 times even though classification required no output file.

### 2.2 Optimization of prompts, pipelines, and agents

Several systems optimize compound LLM programs. DSPy represents LM pipelines
as declarative modules and compiles parameters and demonstrations against a
metric [3]. TextGrad propagates textual feedback through compound systems to
improve prompts and other textual variables [4]. AutoFlow generates and
iteratively optimizes natural-language workflows [5]. AFlow instead searches
over code-represented workflows using Monte Carlo Tree Search and execution
feedback [6]. Automated Design of Agentic Systems (ADAS) broadens the search
space to agent components, tools, prompts, and control flow expressed in code
[7].

PLaND differs in search objective and granularity. It begins with a portable
skill SOP, treats one step as the unit of analysis, and searches for the least
open-ended representation that satisfies fixed quality and resource
guardrails. It does not require every workflow node to become code, and it
records rejected compilations as first-class evidence. This selective boundary
between semantic judgment and deterministic execution is the focus of the
method.

### 2.3 Document classification and dataset quality

Document classification is a useful proof-of-concept because OCR text contains
both semantic content and stable structural cues. We use QS-OCR-Small, which
contains OCR text derived from the 3,482-document Tobacco3482 collection [8].
Recent audits warn that common document benchmarks contain label noise,
ambiguous or multi-label cases, overlaps, and potentially sensitive information
[9, 10]. Lim et al. report that 11.7% of Tobacco3482 samples are improperly
labelled or outside the ontology and that 16.7% permit multiple labels [9]. We
therefore construct our subset only from non-empty documents with exactly one
audited corrected label.

## 3. PLaND Method

### 3.1 Inputs and fixed invariants

PLaND receives workflow requirements, datasource files, a labeled evaluation
CSV, an agent runner, a target accuracy, and resource guardrails. Each eval row
contains `input`, `output`, and `reasoning`, with optional stable identifier and
split fields. The runtime agent receives only the input. Expected output and
annotator reasoning remain hidden.

The following invariants remain fixed during an evolution run:

- runtime model and model digest;
- evaluation inputs, expected outputs, and scorer;
- datasource snapshot and manifest;
- development and validation split assignments;
- random seed and model settings; and
- network and filesystem permission boundary.

Candidate changes may affect the system instructions, one workflow SOP and its
references, tools or scripts invoked by that SOP, and explicitly approved open-
source dependencies.

### 3.2 Step representations

Every SOP step uses one of three representations:

1. **English instruction.** Retained for semantic judgment, ambiguity, or
   open-ended decisions.
2. **Focused reference.** Used when substantial conditional procedure would
   inflate the always-loaded skill.
3. **Executable operation.** A Python or Bash command, or a tightly contracted
   local tool, used for mechanical, stable, bounded behavior.

Conversion is not monotonic. A proposed deterministic implementation is
accepted only when end-to-end evaluation supports it. A script that passes unit
tests but decreases agent accuracy is rejected.

### 3.3 Initial generation

The `generate-initial-version` skill accepts requirements, datasources, an
optional guidance file, a workflow name, and a model provider. It creates:

```text
agent.py
instructions.md
pyproject.toml
data/manifest.json
tools/datasources.py
skills/<workflow>/SKILL.md
```

The generated project contains exactly one workflow skill. Datasource paths,
sizes, and SHA-256 hashes are recorded. For Ollama, the generator declares the
open-source LangChain integration, sets temperature to zero, disables thinking,
uses a fixed seed, disables the default subagent, and hides filesystem tools
outside the read-only workflow. Skill activation is explicit in the application
wrapper because our first smoke test found that model-driven activation was not
reliable for the selected local model.

### 3.4 Evolution loop

The `pland-evolver` skill executes the following loop:

1. Run all development cases from isolated message state.
2. Store output, complete local trace, latency, token usage, errors, and score.
3. Cluster failures and identify unnecessary agent actions.
4. Propose one bounded candidate and record its hypothesis.
5. Run focused unit checks for new deterministic behavior.
6. Rerun development cases under the same conditions.
7. Reject candidates with an accuracy regression or execution errors before
   validation.
8. Run validation only for an eligible frozen candidate.
9. Accept only if validation reaches the target and satisfies token, latency,
   dependency, network, and security guardrails.

The deterministic assessor verifies model, digest, seed, eval path, and split
invariants before issuing `reject_before_validation`,
`eligible_for_validation`, `reject_after_validation`, or `accept`.

## 4. Experimental Method

### 4.1 Data selection

The source corpus contains 3,482 OCR text files across advertisement, email,
form, letter, memo, news, note, report, resume, and scientific classes. We
matched filenames to the independent Tobacco3482 audit by normalized numeric
identifier. We excluded empty OCR text, unmatched files, unknown labels, and
multi-label audit records. This produced 2,724 eligible documents.

Using seed `20260902`, we sorted each class by stable identifier, shuffled each
class, and selected two cases per class. The first became development and the
second validation, producing 10 cases per split. Selection occurred before any
model prediction. Raw OCR remains outside version control because the parent
corpora may contain sensitive information.

### 4.2 Runtime

The experiment ran locally on an Apple Silicon macOS system with 48 GB unified
memory. Ollama 0.33.0 served `qwen3:14b` with digest
`bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`.
Qwen3 supports separate thinking and non-thinking operation [11]; we used
non-thinking mode, temperature 0, and seed 42. The implementation used Python
3.14.7, DeepAgents 0.7.12, and `langchain-ollama` 1.1.0. No paid model service
was called, so estimated model-service cost was USD 0; local compute and energy
were not monetized.

### 4.3 Metrics and guardrails

The deterministic scorer required exact canonical-label equality after parsing
an exact two-field JSON object containing `label` and `confidence`. We report
accuracy, errors, aggregate input and output tokens across all model calls,
mean latency, and nearest-rank p95 latency. The target accuracy was 0.90. An
accepted candidate could not regress validation tokens and could not exceed two
times initial mean validation latency.

The token measure is billed-style aggregate usage reported by the local model
integration. Later agent turns resend accumulated context, so this value is not
the count of unique document tokens.

## 5. Results

### 5.1 Initial agent

The initial agent achieved 9/10 development accuracy. It classified a fax cover
sheet as a letter rather than a form. It used 340,427 aggregate tokens, 13.67
seconds mean latency, and 56.74 seconds p95 latency. The scientific case exposed
21 repeated `write_file` attempts even though the requested output was inline
JSON. This trace motivated a narrower action surface.

On validation, the initial agent achieved 10/10 accuracy with 173,222 tokens,
11.31 seconds mean latency, and 16.09 seconds p95 latency.

### 5.2 Candidate sequence

| Candidate | Development accuracy | Token ratio | Outcome |
|---|---:|---:|---|
| Deterministic signals and read-only tools | 70% | 22.63% | Rejected |
| Read-only filesystem | 80% | 23.96% | Rejected |
| Minimal tools, no default subagent | 80% | 15.62% | Rejected |
| Minimal tools plus label precedence | 100% | 25.55% | Accepted |

The first candidate implemented deterministic counts for features such as email
headers, fillable markers, and scientific terms. Although unit checks passed
and tokens fell substantially, end-to-end accuracy dropped to 70%. The model
over-weighted weak surface evidence, and one case produced an infrastructure
error. PLaND rejected the compiled cue step.

The second candidate removed filesystem write operations but retained the
default subagent. The model delegated unnecessarily, producing invalid JSON on
one case. The third candidate also removed the subagent and reduced tokens to
15.62% of baseline, but email and form were classified as letters. Both were
rejected before validation.

The fourth candidate retained the minimal action surface and added a concise
SOP precedence rule: electronic headers override letter-like content for
email; cover sheets and fillable templates are forms; letter applies only when
neither stronger structure is present. It reached 10/10 development accuracy
and qualified for validation.

### 5.3 Initial versus accepted agent

| Split | Agent | Accuracy | Tokens | Mean latency | p95 latency |
|---|---|---:|---:|---:|---:|
| Development | Initial | 90% | 340,427 | 13.67 s | 56.74 s |
| Development | Accepted | 100% | 86,989 | 22.96 s | 38.50 s |
| Validation | Initial | 100% | 173,222 | 11.31 s | 16.09 s |
| Validation | Accepted | 100% | 92,839 | 12.78 s | 26.48 s |

The accepted agent reduced aggregate validation tokens by 46.40% while
preserving 100% validation accuracy. Mean validation latency increased 13.04%
and p95 latency increased from 16.09 to 26.48 seconds. On development, tokens
fell 74.45% and accuracy increased by 10 percentage points, but mean latency
rose 67.91%. The accepted result therefore improves accuracy and token expense
under the configured latency guardrail, not every objective simultaneously.

## 6. Discussion

### 6.1 Determinism is a constrained optimization target

The rejected deterministic signal extractor illustrates the core PLaND
principle. A function may be deterministic, cheap, and unit-tested while still
being the wrong representation for a semantic boundary. Converting more English
to code is not itself success. The conversion must survive end-to-end
development and validation evidence.

Conversely, reducing the model's available actions was beneficial even though
it did not compile a semantic classifier. The initial tool surface allowed
irrelevant writing and delegation. Each additional tool created another
possible action and enlarged tool descriptions in the prompt. Restricting the
surface reduced tokens, prevented a repeated-action failure, and made remaining
classification errors easier to attribute.

### 6.2 The role of natural language after evolution

The accepted SOP is hybrid rather than fully compiled. File access and tool
availability are deterministic. Label selection remains natural language,
augmented by a short precedence rule learned from development failures. This is
consistent with the slogan: **code steps bypass unnecessary model reasoning;
English steps preserve semantic flexibility.**

### 6.3 Cost, accuracy, and latency conflict

The results also caution against optimizing tokens alone. Candidate 003 used
the fewest development tokens but failed the quality guardrail. Candidate 004
preserved validation accuracy and reduced tokens, yet latency increased. Local
latency depends on generation length, repeated turns, model residency, and
system contention; it does not move monotonically with token counts in one
small run. Multi-objective acceptance rules and repeated measurements are
therefore necessary for stronger conclusions.

### 6.4 Small per-run savings become material at enterprise scale

The absolute savings in a 20-document proof-of-concept can appear modest, but
agent expense is multiplicative with deployment volume. In the frozen-prompt
follow-up experiment, the hybrid SOP reduced validation usage by 27,317 tokens
across 10 documents, or approximately 2,732 tokens per document, while
preserving accuracy. If the same per-document difference held across one
million comparable documents, it would avoid approximately 2.73 billion model
tokens. The measured mean-latency difference of 2.71 seconds per document would
also correspond to roughly 31 days of aggregate processing time across one
million documents, although parallel execution means this is not equivalent to
31 days of calendar latency.

This calculation is an illustration, not a production forecast: document mix,
model serving, batching, caching, concurrency, hardware utilization, and price
all affect realized savings. The broader implication is that repeated
model-mediated interpretation has a cumulative cost. Enterprises executing
millions of documents, workflow steps, or agent runs can therefore benefit
substantially from even moderate per-execution reductions, provided quality and
operational guardrails continue to hold at scale.

## 7. Limitations and Threats to Validity

This proof-of-concept has several material limitations:

1. Only 20 documents were evaluated, with one case per class in each split.
2. There is no held-out set; validation was used for candidate acceptance.
3. Each agent/split combination was run once with one model and one seed.
4. Accuracy values therefore have high uncertainty and cannot establish
   population-level performance.
5. QS-OCR-Small contains historical tobacco-industry documents and inherited
   OCR errors, label ambiguity, distribution bias, and privacy risks.
6. The experiment classifies existing OCR text, not raw images or PDFs.
7. Token measurements are integration-reported aggregate usage, not energy or
   monetary cost.
8. The accepted precedence rule may be specific to the selected development
   boundary.
9. Explicit skill activation in the wrapper limits conclusions about purely
   model-driven skill discovery.
10. The generator's Ollama harness settings may not transfer unchanged to
    other model providers or agent frameworks.
11. Both the initial and accepted SOPs contain only English steps. The accepted
    agent is hybrid at its tool and harness boundary, but this experiment does
    not establish an accepted natural-language-SOP versus hybrid-SOP comparison;
    the command-oriented candidate was rejected.

Future work should use larger audited held-out sets, repeated seeds, multiple
local models, confidence intervals, energy measurements, step-level ablations,
and tasks beyond classification. A particularly useful ablation would separate
the token effect of tool removal from the accuracy effect of SOP precedence.

## 8. Conclusion

PLaND provides an eval-guided method for evolving Agent Skills toward the least
non-determinism that preserves task quality. It separates semantic judgment
from stable execution, freezes evaluation invariants, and treats rejected
compilation attempts as evidence rather than silently optimizing toward a
cheaper but worse agent. In the reported small-scale document-classification
experiment, the accepted hybrid agent preserved 100% validation accuracy and
reduced aggregate validation tokens by 46.40%, at the cost of 13.04% higher
mean latency. A deterministic signal extractor reduced expense further but was
correctly rejected after quality regression. These results support selective,
guardrailed evolution rather than wholesale replacement of skill text with
code.

## References

[1] Agent Skills. “Agent Skills Specification.” https://agentskills.io/specification

[2] LangChain. “DeepAgents: Skills.” https://docs.langchain.com/oss/python/deepagents/skills

[3] O. Khattab et al. “DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines.” arXiv:2310.03714, 2023. https://arxiv.org/abs/2310.03714

[4] M. Yuksekgonul et al. “TextGrad: Automatic Differentiation via Text.” arXiv:2406.07496, 2024. https://arxiv.org/abs/2406.07496

[5] Z. Li et al. “AutoFlow: Automated Workflow Generation for Large Language Model Agents.” arXiv:2407.12821, 2024. https://arxiv.org/abs/2407.12821

[6] J. Zhang et al. “AFlow: Automating Agentic Workflow Generation.” arXiv:2410.10762, 2024. https://arxiv.org/abs/2410.10762

[7] S. Hu, C. Lu, and J. Clune. “Automated Design of Agentic Systems.” NeurIPS 2024. https://arxiv.org/abs/2408.08435

[8] QuickSign. “Quicksign OCRized Text Dataset (QS-OCR).” https://github.com/QuickSign/ocrized-text-dataset

[9] G. Lim, S. Larson, and K. Leach. “Label Errors in the Tobacco3482 Dataset.” arXiv:2412.13140, 2024. https://arxiv.org/abs/2412.13140

[10] S. Larson, G. Lim, and K. Leach. “On Evaluation of Document Classification using RVL-CDIP.” arXiv:2306.12550, 2023. https://arxiv.org/abs/2306.12550

[11] A. Yang et al. “Qwen3 Technical Report.” arXiv:2505.09388, 2025. https://arxiv.org/abs/2505.09388
