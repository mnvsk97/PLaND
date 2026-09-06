# September 5 line by line review response

This record covers the forty numbered notes collected while the author reviewed the seven-page PDF, and the final approval of the later sections. Locations refer to section names and text anchors, since the revised paper is longer.

## Applied editorial changes

| Note | Reviewed location or anchor | Pointed change and status |
| --- | --- | --- |
| 1 | Abstract, predefined quality contract | Replaced the unexplained phrase with accuracy limits set before evaluation. The abstract now states the actual thresholds; Sections 2.3 and 3.3 define them. Applied. |
| 2 | Abstract, evolver skill | Section 2.2 describes what the skill tells the host agent to do. Appendix D summarizes its contents and links to the full file. Applied. |
| 3 | Abstract, entirely English SOP | Introduced generate-initial-version with pland-evolver in Section 2.2; expanded in Appendix D. Kept the abstract focused, as requested. Applied. |
| 4 | Abstract, scorer | Removed the unexplained term there. Defined exact-match scoring in Section 2.2 and identified the implementation in Appendix B.1. Applied. |
| 5 | Abstract, unequal sample sizes | Section 3.1 now distinguishes prepared split sizes from completed evaluations and explains the stopping rule. Replacement results require the separate 1,000-case study to finish. Partly applied; results pending. |
| 6 | Abstract, predefined acceptance criteria | Replaced with explicit accuracy and token requirements. Section 3.3 explains all four in plain language, with the exact rule and protocol link in Appendix B.3. Applied. |
| 7 | Abstract, autonomous rule discovery limitation | Preserved the approved sentence. Applied. |
| 8 | Keywords | Retained agent skills and added SOP evolution. Applied. |
| 9 | Introduction, practical question | Added a colon, capitalized the direct question, and ended it with a question mark. Applied. |
| 10 | Introduction, executable rule | Defined executable step at first use; named the Python classification script when discussing these experiments. Applied. |
| 11 | Section 2.1, templates | Specified document templates, images, and lookup tables with the Agent Skills source. Applied. |
| 12 | Section 2.1, earlier SOPs call this a command | Removed the sentence. Applied. |
| 13 | Figure 1, future graph organization | Caption now explains how recurring production paths could become graph steps, with a reference to existing orchestration tools. Section 6 develops the proposal without asserting industry inevitability or a measured result. Applied. |
| 14 | Section 2.2, task-specific scorer | Defined the runner, scorer, expected label, and accuracy explicitly. Appendix B.1 explains inputs and outputs. Applied. |
| 15 | Section 2.2, development validation test | Explained each split's purpose and why unseen examples are needed. Applied. |
| 16 | One LEDGAR name and split sizes | Tables use simple dataset names; Table 1 states the prepared development, validation, and reserved-test counts for all three datasets. Applied to existing evidence. |
| 17 | Equal 1,000-case evaluations and three repetitions | Defined split versus paired repeated run. The separate worktree has an active protocol for three paired runs on 1,000 validation cases per dataset. Its results are incomplete and are not substituted into this manuscript. Partly applied; new measurements pending. |
| 18 | Section 2.2, ten candidates | Explained the attempt limit and linked stopping conditions in Appendix D. Disclosed that the saved fixed-package comparisons do not establish the number of autonomous proposals. Applied. |
| 19 | Define candidate search and evolution | Defined all three in Section 2.2 and added a five-step process. Applied. |
| 20 | Add the LEDGAR worked example | Added the illustrative governing-law clause, baseline response, pattern-based proposal, fallback, and evaluation on separate cases. Clearly marked it as an explanation rather than a recorded discovery trace. Applied. |
| 21 | Figures 2 and 3 | Preserved the supplied images. Figure 2's caption describes the fixed setup. Figure 3's caption defines candidate, search, acceptance, and the reserved test after its Yes branch. The companion Figure 3 specification below records the proposed Excalidraw revision. Caption applied; replacement image pending author supply. |
| 22 | Section 2.2, saved fixed SOP paragraph | Replaced the dense paragraph with direct statements about measuring saved packages and not testing automatic rule discovery. Applied. |
| 23 | Table 1, only LEDGAR has 1,000 | Table 1 now shows all prepared splits. It does not falsely claim the reserved CFPB or SpamAssassin tests were executed. Final evaluation counts await the separate study. Partly applied. |
| 24 | Dataset label/source references | Kept primary dataset citations in Section 3.1; moved full labels, selection methods, source mapping, and audit references to Appendix C. Applied. |
| 25 | Section 3.1, LEDGAR selection explanation | Replaced the convoluted paragraph with the common split design and a short explanation of completed evaluations. Applied. |
| 26 | Section 3.1, validation-only CFPB/SpamAssassin | This factual limitation remains until replacement measurements exist. It cannot be removed on the basis of preparation alone. Pending new results. |
| 27 | Section 3.2, baseline | Defined baseline and hybrid in Section 1, then referenced that definition at the start of Section 3.2. Applied. |
| 28 | Section 3.2, fallback | Explained trying Python first, using its answer on a unique match, and sending unresolved cases to the same model. Applied. |
| 29 | Section 3.2 is confusing and misplaced | Renamed to How the baseline and hybrid classify each case. Kept the simple execution example in the main text and moved function-call, output-validation, and marker details to Appendix B. Applied. |
| 30 | Section 3.3, lower end of 95% | Introduced an uncertainty range, explained pairing, and gave the LEDGAR 0.8-point observed versus 1.6-point lower estimate. Applied. |
| 31 | Simpler statistical language | Numbered requirements lead with accuracy/token safety checks. Appendix B.3 preserves the exact percentile bootstrap definition and avoids interpreting the lower endpoint as a guaranteed worst case. Applied. |
| 32 | Section 3.4, rather than in the main description | Removed the phrase. Applied. |
| 33 | Section 3.4, inference seed | Put the definition, seed values, and distinction from selection/resampling seeds in Appendix B.2. Main text points there. Applied. |
| 34 | Section 3.4, two-worker concurrency | Replaced with the local setup allowing at most two requests at the same time. Applied. |
| 35 | Section 3.4, pair/run arithmetic | Main text describes three paired repetitions directly. Moved exact execution totals to Appendix B.2. Applied. |
| 36 | Section 4.1, the script | Named the Python classification script. Applied. |
| 37 | Section 4.1, fixed 0.99 marker | Explained that 0.99 is hard-coded, while measured accuracy on the routed clauses is 395/411 = 96.11%. Appendix B explains that the runner does not enforce calibrated 99% confidence. Applied. |
| 38 | Sections 4.2 and 4.3, further tailoring | Added task-specific SOP/rule development as an untested possibility outside the comparison. Kept the methodology skills task-agnostic and avoided claiming equal development effort or proven gains. Applied. |
| 39 | Section 6, workflow generation from runtime evidence | Added the requested proposal for using logs, recurring paths, failures, and model use to generate a future workflow graph, subject to separate evaluation. Applied. |
| 40 | Data and Code Availability | Checked the linked pinned artifacts, exact main-result bytes, manifests, scorer, and verification entry point. Corrected the old snapshot's protocol path to experiments/confirmatory-study.json. Clarified that offline verification does not run model inference and that exact CFPB regeneration requires the unshared snapshot. Applied for current evidence; repeat when new results are integrated. |
| Final approval | Sections 5, 5.2, 5.3, 6, and 7 | Sections 5 and 7 are byte-for-byte unchanged from the reviewed Markdown. Section 6 has only the requested runtime-to-workflow paragraph added. Existing figures remain byte-for-byte unchanged. |

## Remaining dependencies

The active experiment lives in `/Users/saikrishna/.codex/worktrees/bd1a/deterministic-skills`, under `experiments/paired-1000-validation/`. The prospective protocol specifies 1,000 validation examples per dataset, three paired runs, fixed packages, and reserved tests that are not evaluated in that study. This is not evidence of 1,000 completed final-test evaluations for all datasets. The final paper must describe the stage actually measured. Do not rename validation observations as test observations or open an unreleased test merely to make the result tables uniform.

After all new comparisons complete and their evidence is verified, update the abstract, Table 1, Sections 3.1 and 3.4, Tables 2-4, Sections 4.1-4.3, the numerical/evaluation-stage statements in Sections 5 and 7, Data and Code Availability, and Appendices A-C together. Keep the approved prose wherever the new evidence does not require a change.

## Figure 3 specification for Excalidraw

Preserve Figure 2. It explains what may change during a comparison. The author offered to supply a revised Figure 3; no replacement image has yet been supplied.

Use this sequence in the revised Figure 3:

1. Current SOP.
2. Run on development examples and record answers, errors, model calls, and tokens.
3. Propose one change to create a candidate SOP package.
4. Evaluate the baseline and candidate on separate validation examples.
5. Decision: Does the candidate meet all acceptance requirements?
6. No branch: reject, retain the current SOP, and return to development evidence within the attempt limit. A new candidate requires an unused evaluation set.
7. Yes branch: freeze the selected candidate, then assess it on the reserved test without tuning.

Include small definitions: Candidate = one proposed revised SOP package. Search = proposing and evaluating successive candidates. A note can say that repeated runs of the same package measure repeatability, not further evolution.

## Review and verification

The first complete reading checked the logic from the abstract through the appendices against the forty notes. It led to earlier definitions, the worked example, relocation of technical details, and shorter statistical explanations. The second reading checked claim strength and consistency with source code and archived results; it corrected the protocol link, removed an overbroad statement about the absence of later tailoring, clarified the example's illustrative status, and removed the remaining inference-seed explanation from the main text.

The paper audit recalculates saved metrics and paired bootstrap intervals. Link checks resolve the manuscript's URLs and inspect pinned Git objects; the CFPB page was available through the web reader even though direct scripted access returned HTTP 403. Render checks cover every page and the single-column tables. The first render exposed a split equation block; the builder now keeps it together and also prevents individual references from splitting across columns. Final checks are recorded in the local task output.
