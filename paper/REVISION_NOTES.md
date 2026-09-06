# PLaND revision and review record

Revision dates: September 4–5, 2026, Pacific time.

Scope: revise the manuscript and its matching PDF, Word, and HTML; preserve the original diagrams. Retain only LEDGAR, CFPB, and SpamAssassin in the reported study. Out-of-scope dataset experiments and local data were subsequently removed. No model experiments were rerun for this revision.

Sources of feedback: the annotated nine-page PDF in this task and the September 4 live discussion, [Wispr Paper Revision Feedback](https://notes.wisprflow.ai/shared/ZQnKepL0XU4y2zaVXNRWJcOeUFCStlixZwmOAH3y4Ks), 9:34–10:51 p.m. Pacific, identified by the user as the discussion with Asit. Speaker numbers in the transcript are not assigned to named individuals here.

The original page locations below refer to the reviewed PDF, not to pagination after revision. New section numbers and paragraph anchors are the stable revision locators.

## Feedback and its disposition

| Reviewed location and exact anchor | Feedback | Revised location and action |
| --- | --- | --- |
| Entire paper; dataset scope | Keep only LEDGAR, CFPB, and SpamAssassin. | Abstract; Section 3.1, Table 1; Sections 4.1–4.3. Removed the document/OCR datasets, their rows, pilot narratives, unused bibliography entries, experiments, and local caches. |
| Entire paper; “quality-first” | Remove the additional study and all dependent discussion. | Removed its section and table, abstract/conclusion claims, policy comparisons, and associated caveats throughout the manuscript. |
| p. 4, “0.50” | Where did this value come from? | Removed the extraction-quality threshold with the out-of-scope extraction dataset. It is not presented as a classification criterion. |
| p. 4, “LiteParse supplied an OCR condition rather than a separate dataset” | Which dataset was parsed? | This referred to SROIE, not an independent dataset. The sentence and reference are removed with the entire excluded track. |
| p. 4, “seeds 20260903, 20260904, and 20260905” | Remove seed numbers from prose. | Section 3.4 defines what seeds do. Appendix B points to exact values in manifests without listing them in the main narrative. |
| p. 4, “Ollama 0.33.0 … digest” | Simplify the setup; move identifiers to the end. | Section 3.4 states model, hardware, and main execution settings. Appendix B contains the recorded repeated-run version and digest. It does not retroactively claim all original options were identical. |
| p. 4, “two-worker runtime” | An environment constraint, not an experimental requirement. | Section 3.4, paragraph beginning “The repeated runs used…” explicitly makes that distinction. |
| p. 4, “primary held-out evidence … release policy was frozen” | Explain the sequence in plain language. | Section 3.1, final paragraph; Section 3.3; Figure 3. Validation decides whether the fixed candidate proceeds to a previously unused test. |
| p. 5, results table, LEDGAR validation and test rows | Why two LEDGAR entries? | Tables 1–3 now report one 1,000-clause LEDGAR evaluation, labelled LEDGAR. Section 3.1 briefly discloses the separate earlier selection check; its results are omitted. |
| p. 5, results table, “Baseline nonviable” | Undefined and unclear. | Those excluded rows are removed. Section 2.3 defines minimum usable accuracy; retained rejection rows use direct wording rather than the old label. |
| p. 5, “hybrid minus NL accuracy was -0.8 percentage points…” | Too complicated. | Section 4.1 opens with 935 versus 927 correct answers: eight fewer out of 1,000. The interval and two-point allowance are explained separately. Table 3 labels the units explicitly. |
| p. 5, “This caveat is important … current evolver policy…” | Remove the confusing comparison between LEDGAR studies. | Replaced by Section 3.2, final paragraph, and Section 4.1, final paragraph. The evaluated candidate changed both routing and fallback wording; no later-study comparison is needed. |
| p. 5, “the 80% floor” | Where did the number come from? | Section 2.3, final two paragraphs, cites the saved configuration, names it as a study choice, and states that no application-specific error-cost justification is recorded. |
| p. 5, “release contract” | Where is it defined? | Replaced by the four numbered acceptance criteria in Section 3.3, before the results. |
| p. 5, “three multimodal confirmatory tracks…” | Remove these datasets. | Removed entirely, together with dependent discussion and references. |
| p. 5, six numbered quality-first requirements | Keep the clear numbered structure, not this study. | Section 3.3 uses a numbered list for the actual retained protocol: absolute accuracy, allowed-loss interval, observed token reduction, and positive token-reduction interval. |
| p. 5, “Earlier pilot and robustness evidence” | Rethink or remove after narrowing scope. | Removed the pilot section/table. The main results are one protocol; three later repeats are clearly separated in Appendix A. |
| p. 6, claim-to-evidence table, “Not established / Not tested” rows | Unclear and bundled. | Removed the table. Generation limits now follow generation methods (Section 2.2); execution details follow the runner description (3.2); resource limits follow token interpretation (5.2); workflow generalization follows task scope (5.3). |
| p. 6, “The main systems argument is…” | Strong discussion; preserve. | Section 5.1 preserves the argument and its progression from mixed decisions to selective computation. Fraud detection remains a motivating example, not a tested dataset. |
| p. 6, “The later quality-first study…” | No longer needed. | Removed. Section 5.1 interprets only the retained three-dataset results and their stated tolerance. |
| p. 7, “pattern-discovery algorithm … arbitrary execution histories” | Are we using datasets or run histories? | Section 2.2, second paragraph, explains that dataset inputs produce execution histories. Development histories inform changes; validation/test examples evaluate them. The following limitation identifies precisely what was not separately measured. |
| p. 7, “prompt shortening” | Architectural decision or side effect? | Section 3.2 states, following the live clarification, that shortening arose during candidate generation rather than as a separately specified architectural change. Section 4.1 avoids claiming a causal ablation that was not run. |
| p. 7, “CPU, memory, storage, network…” | Generation considers these, but validation uses tokens. | Section 5.2 makes this distinction explicit. Tokens are the sole efficiency acceptance measure; calls explain the mechanism. No measured dollar, energy, or latency-saving claim is made. |
| p. 7, “command” | What does it mean? | Section 2.1 defines executable steps. Section 3.2 explains that the benchmark imports the classifier function rather than testing autonomous shell execution. |
| p. 7, “The later quality-first study corrects the protocol issue…” | Rewrite after removing that study. | Removed. The local bundled-change limitation remains in Sections 3.2 and 4.1 without obsolete follow-up claims. |
| p. 7, “candidate-generation policy is agentic … schema-v2 document pilot…” | Incomprehensible bundled limitations. | Removed the mixed paragraph. Relevant limitations are placed beside their methods/results; excluded pilots are not discussed. |
| p. 7, “two-point non-inferiority margin” | Explain and cite earlier. | Section 2.3 defines epsilon with a concrete numerical example. Section 3.3 explains the paired interval. Reference 13 supports the testing concept, not the numerical choice. |
| p. 8, “program synthesis methods” | Use clearer language. | Section 6 says “methods for generating code from examples or execution records.” |
| p. 8, “Three optimized replications” | Repetition count appears too late. | Section 3.4 introduces three additional paired runs per dataset and their purpose before Results. Appendix A supplies Table 4 and variability details. Main and repeated settings are not pooled. |
| p. 8, “A later quality-first study used fresh 500-case validation sets…” | Remove. | Removed from the abstract, Results, Discussion, and Conclusion. |
| p. 8, “do not prove general autonomous pattern discovery…” | Reassess after removing studies. | Section 2.2 now gives a specific limitation: independent candidate-generation success was not measured. Removing unrelated experiments does not turn fixed-SOP execution into a generation benchmark. The conclusion focuses on what was tested. |
| Live discussion, graph-based SOP | Future state, not implemented result. | Introduction and Figure 1 label the graph as proposed; no particular graph framework is required. |
| Live discussion, industry paragraph | Distinguish prior infrastructure and related research from PLaND. | Introduction, paragraphs 2–3, with references 1–11. |
| Live discussion, missing experiment overview | Explain datasets, conditions, and number of runs before results. | New Section 3 and Table 1 precede all result tables. Main results: three pairs/six runs. Repeats: nine pairs/eighteen runs. |
| Live discussion, skill anatomy and “references” | Explain before using these terms. | Section 2.1 defines SKILL.md, references, scripts, and assets, with the Agent Skills specification citation. |
| Live discussion, E, Q, epsilon, viability, and “development” | Define symbols and terms where introduced. | Sections 2.2–2.3 define them before equations and figures using them. |
| Live discussion, two-level taxonomy | Simplify operation-versus-decision-region discussion. | Removed the taxonomy. Section 5.1 uses one concrete interpretation: selected inputs can use rules while other inputs still use the model. |
| Live discussion, future work | Focus on a few contextual next steps. | Section 6 prioritizes generation from development histories, stateful workflows, and longitudinal rule monitoring/rollback. |

## Ten review passes

These are ten distinct reviews of the revision, with different failure modes checked. They are not ten new experiments or independent peer reviews.

| Pass | Review focus | Evidence and corrections | Status |
| --- | --- | --- | --- |
| 1 | Scope across the complete manuscript | Removed excluded datasets and additional study from all sections, tables, captions, and bibliography; audited forbidden terms. Preserved archived evidence. | Complete |
| 2 | Narrative and experimental sequence | Read the outline and manuscript for unexplained transitions; placed definitions and setup before results; separated one main protocol from repeated measurements. | Complete |
| 3 | Method and implementation fidelity | Checked SOPs, classifier functions, runner options, comparison code, split manifests, and repeated-run preflight. Corrected confidence-marker and shell-command claims; distinguished original JSON settings from repeated structured output. | Complete |
| 4 | Statistical and numerical accuracy | Recalculated all four main accuracy/token comparisons and 5,000-resample paired intervals from saved per-case records. Checked acceptance settings, repeat means, and split sizes. audit_paper.py passed. | Complete |
| 5 | Bibliography and citation support | Checked primary documentation, arXiv metadata, ACL dataset sources, official data sources, and statistical references. Corrected four working-draft paper titles; added LexGLUE, non-inferiority, bootstrap, and evidence citations. Numerical tolerances are not attributed to outside authorities. | Complete |
| 6 | Plain language and terminology | Read the complete rewrite for jargon, unexplained abbreviations, relative-percent versus percentage-point ambiguity, repetition, and reader assumptions. Replaced release/test-opening jargon and defined executable steps, fallback, and seed. | Complete |
| 7 | Claim strength and feedback coverage | Matched every annotated comment and the live discussion to the table above. Kept contextual limits on fixed-SOP execution, prompt-change attribution, local-model repeatability, and real-world generalization. | Complete |
| 8 | PDF and Word visual review | Inspected all pages, three figures, three native equations, four tables, and headings. After the user's format correction, restored the original SVG diagrams exactly and inspected all eight pages of the two-column render. Fixed split figure captions and kept each small table together. | Complete |
| 9 | Reproduction and artifact consistency | Repository tests passed in all 12 test directories. All eight evidence manifests (131 files) passed unchanged. The artifact audit matched source identifiers, all Word paragraphs/table cells in the PDF, citations, and repeated-run records. Paper-file hashes updated; archived evidence hashes untouched. | Complete |
| 10 | Final complete-paper read and regression review | Reread the complete manuscript against the feedback map. Checked every section/table/figure locator and citation order, synchronized the README, verified no excluded content or lost text in the outputs, and confirmed no experiment/data/skill files changed. | Complete |

## Final verification

- Final manuscript: eight A4 pages, with matching PDF, Word, HTML, and Markdown.
- Three reported main paired comparisons reproduce the saved accuracy, tokens, acceptance decisions, and paired intervals.
- Eighteen repeated-run files reproduce the appendix means and zero label disagreements.
- Eighteen references appear in first-citation order; all four tables and three figures have valid callouts.
- The updated manuscript SHA-256 is `873a59429a33dd781d3d6b671e51442782b543498db05db3fda30cc0f966442b`.
- No new model inference, data deletion, experiment alteration, push, or submission was performed. The user subsequently authorized a local check-in after the clarity review below.
- The first repository-test attempt used the document runtime, which lacked LangChain. Repeating the check with the existing locked `reproduce/.venv` environment passed. This was an environment mismatch, not an experiment-code change.

## Rebuilding

Run `paper/build_artifacts.cjs` with Node dependencies `sharp` and `marked` available and `PLAND_PYTHON` pointing to a Python environment with python-docx and Pillow. This creates Word and HTML from PLaND.md, reading the unchanged SVG figures as inputs. Render Word with the document renderer to PDF, and visually inspect every page. The repository verification command is `python reproduce/verify.py`; the paper-specific audit is `python paper/audit_paper.py --artifacts` and requires pypdf. The artifact audit recomputes statistics from saved outputs without model inference.

## Format correction after review

The user specified [SAS article 21609](https://saspublishers.com/article/21609/) as the visual reference and explicitly prohibited diagram changes. All three SVG files were restored byte-for-byte to their original repository versions. The diagram generator introduced during revision was removed. PDF and Word now use full-width front matter, two-column body text, Times New Roman, blue major headings, and full-width result tables. Publication branding, DOI, acceptance dates, and license statements from the reference article were not copied. HTML retains the same text and original diagrams with a responsive two-column layout. The manuscript source and reported results are unchanged by this formatting correction. All eight final PDF/Word pages were visually inspected; the numerical and artifact audit passed again.

## Single LEDGAR result revision

At the user's request, the main paper now reports only the existing 1,000-clause LEDGAR evaluation and calls it LEDGAR. The 100-clause selection result was removed from Tables 2 and 3; Table 1 now lists evaluated sample sizes instead of three split columns. Section 3.1 preserves the selection-history disclosure. The abstract, results, conclusion, appendix labels, evidence-file pointers, and run counts were updated consistently. Main results now comprise three pairs/six runs, with nine repeated pairs/eighteen runs in Appendix A: twelve pairs/twenty-four reported runs. No results were rerun or changed, and the original SVG diagrams remain unchanged. The eight-page PDF and Word render was inspected after rebuilding in the reference article's two-column layout with full-width abstract styling.

## Two complete clarity reads before check-in

On September 5, the manuscript was read from title through references twice: first from the Markdown as a first-time reader, then from the complete eight-page PDF text against the feedback record. The rendered results and appendix pages were also checked for readable tables and reference placement. No further manuscript edits were needed for this checkpoint.

- First read: the problem, English-only baseline, hybrid execution, fallback, evaluated datasets, accuracy/token measures, and main conclusion form a coherent sequence. LEDGAR has one main 1,000-clause result.
- Second read: checked the earlier feedback, selection-history disclosure, distinction between fixed-SOP execution and rule generation, study-specific thresholds, prompt-shortening caveat, repeated-run settings, contextual limitations, and citation roles. Dataset references describe the sources; the statistical references support methods rather than numerical tolerances; reference 12 and Data and Code Availability identify the experimental evidence.
- Confirmed that the three cited main comparison files exist at the pinned evidence commit. The numerical/artifact audit rechecked all three main comparisons and nine repeated pairs, citation order, table/figure callouts, and source-to-PDF text consistency.
- Assessment: suitable to check in as the current clarity baseline for a technically interested first-time reader. This is an editorial self-review, not independent peer review or a guarantee that no reader will have questions. Rule-generation success, application-specific threshold justification, and attribution of all savings to routing remain explicitly disclosed evidence limitations.
- Original diagrams, current layout, reported numbers, and manuscript wording were preserved during these two reads. Local commit authorized by the user; no push or publication action authorized.
