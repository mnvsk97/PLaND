# PLaND fresh evaluation report

## Technical summary

The frozen Gemini 3.5 Flash Lite study completed all planned development and
selection repeats for LEDGAR, CFPB, and SpamAssassin. LEDGAR and SpamAssassin
passed selection and therefore completed all three 500-case final-test pairs;
CFPB was rejected at selection because its hybrid accuracy was below the 80%
absolute floor in every repeat, so its final test remained unopened. On the
first final-test repeat, LEDGAR changed accuracy from 94.8% to 95.8% while
reducing model calls from 500 to 130 and tokens by 74.6%; SpamAssassin changed
accuracy from 97.8% to 97.2% while reducing calls from 500 to 323 and tokens by
28.1%. These results compare fixed English and hybrid SOP execution; they do
not independently establish autonomous rule-discovery reliability.

## Study contract and completed scope

| Item | Frozen value |
| --- | --- |
| Study ID | `gemini-3.5-flash-lite-2026-09-05-11-41-pm`, with SpamAssassin amendment 02 |
| Base plan SHA-256 | `57f613822481e0d95cecba0105fe227b96476c70ea9568848f0f0bcc0934eccd` |
| Spam amendment-02 plan SHA-256 | `35c4c89d99f7cd788a38f2e36ea46ca75beb58ee9e5fcab44019b5a66036bea7` |
| Evidence manifests | LEDGAR `4ce8cc9c...`; CFPB `48b73abe...`; SpamAssassin `27d0e160...` |
| Datasets | LEDGAR; CFPB; SpamAssassin |
| Split sizes per dataset | 500 development; 1,000 selection; 500 final test |
| Evaluated model | `google/gemini-3.5-flash-lite`; OpenRouter to Google AI Studio; configuration `d703b8e16a3dc88aa1ac6a47171414c3873ee8f064db5bb911c5d67252fd9c4d` |
| Seeds | Dataset/inference `20260902`; repeats `20260903`, `20260904`, `20260905` |
| Runtime | DeepAgent 0.7.12; low reasoning; non-streaming; 1,024-token output cap; 300-second timeout; 8 workers; no provider fallback |
| Baseline readiness | Accuracy >=80%; normal completion; no evaluation errors; maximum 10 English attempts |
| Candidate budget | Maximum 10 development-only attempts; first ready candidate frozen for selection |
| Selection gates | Both accuracies >=80%; paired accuracy lower bound >=-2 pp; tokens reduced >=5%; paired token-reduction lower bound >0; no evaluation errors |
| Uncertainty | 5,000 paired bootstrap resamples; Wilson intervals; exact McNemar test |

Collection outcome: **complete**. LEDGAR and SpamAssassin final tests completed;
CFPB's reserved 500-case final test remained unopened. Provider-blocked
SpamAssassin cases were replaced one-for-one with same-label, previously
unopened cases, retaining 1,000 balanced selection cases. Superseded partial
runs and two resumed connection interruptions remain preserved.

## Main results

The table reports repeat seed `20260903`; the other repeats are below.

| Dataset | Reported stage | Cases | Baseline accuracy | Hybrid accuracy | Difference (pp), 95% paired CI | Model calls | Tokens | Token reduction, 95% paired CI | Decision |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |
| LEDGAR | Final test | 500 | 94.8% | 95.8% | +1.0 [-0.4, +2.6] | 500 -> 130 | 242,557 -> 61,653 | 74.6% [70.6%, 78.4%] | Pass |
| CFPB | Selection | 1,000 | 80.0% | 79.4% | -0.6 [-1.6, +0.4] | 1,000 -> 788 | 700,508 -> 536,424 | 23.4% [20.6%, 26.3%] | Reject: absolute floor |
| SpamAssassin | Final test | 500 | 97.8% | 97.2% | -0.6 [-1.6, +0.4] | 500 -> 323 | 1,464,817 -> 1,052,802 | 28.1% [22.1%, 35.2%] | Pass |

LEDGAR passed all selection gates and all three final-test comparisons. CFPB
met the relative noninferiority and token gates, but its hybrid selection
accuracy was 79.4%, 78.9%, and 79.5%, below the frozen 80% floor; selection was
therefore rejected. SpamAssassin passed all three amended selection pairs and
all three final-test comparisons after two selection provider blocks were
replaced without reducing the sample.

## Acceptance-gate audit

| Dataset and stage | Invariants | Baseline >=80% | Hybrid >=80% | Accuracy lower >=-2 pp | Tokens >=5% | Token lower >0 | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LEDGAR - selection | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| LEDGAR - final test | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| CFPB - selection | Pass | Fail in repeats 2-3 | Fail | Pass | Pass | Pass | Reject |
| SpamAssassin - selection | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| SpamAssassin - final test | Pass | Pass | Pass | Pass | Pass | Pass | Pass |

## Baseline readiness and candidate provenance

| Dataset | Frozen baseline development accuracy, seed 1 | Baseline SOP SHA-256 | Candidate | Candidate SOP / classifier SHA-256 | Development decision |
| --- | ---: | --- | --- | --- | --- |
| LEDGAR | 96.6% | `187274d0...` | candidate-02 | `cfb84b4d...` / `803295f0...` | Ready |
| CFPB | 82.0% | `70deb8e1...` | candidate-02 | `6610c6ed...` / `f808502f...` | Ready |
| SpamAssassin | 98.6% | `b3c9ec9c...` | candidate-01 | `08e44ddb...` / `99498926...` | Ready |

The fixed candidates performed selective deterministic classification and used
the English SOP as the exact model fallback. On the first reported comparison,
command resolution covered 69.8% of LEDGAR, 21.2% of CFPB, and 35.4% of
SpamAssassin cases; remaining cases fell back to the model. Saved case-level
traces retain matched rules, abstentions, guard outcomes, execution errors, and
fallbacks. This is package provenance, not a separate estimate of autonomous
discovery success.

## Repeatability of the frozen comparison

| Dataset-stage | Seed | Pair order | Baseline acc. | Hybrid acc. | Baseline tokens | Hybrid tokens | Decision |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| LEDGAR-final | 20260903 | B -> H | 94.8% | 95.8% | 242,557 | 61,653 | Pass |
| LEDGAR-final | 20260904 | H -> B | 95.0% | 95.8% | 242,421 | 61,700 | Pass |
| LEDGAR-final | 20260905 | B -> H | 95.0% | 95.8% | 242,372 | 61,707 | Pass |
| CFPB-selection | 20260903 | B -> H | 80.0% | 79.4% | 700,508 | 536,424 | Reject |
| CFPB-selection | 20260904 | H -> B | 79.6% | 78.9% | 700,526 | 536,141 | Reject |
| CFPB-selection | 20260905 | B -> H | 79.6% | 79.5% | 700,470 | 536,111 | Reject |
| SpamAssassin-final | 20260903 | B -> H | 97.8% | 97.2% | 1,464,817 | 1,052,802 | Pass |
| SpamAssassin-final | 20260904 | H -> B | 97.4% | 97.0% | 1,465,131 | 1,052,891 | Pass |
| SpamAssassin-final | 20260905 | B -> H | 97.8% | 97.4% | 1,464,835 | 1,052,948 | Pass |

These repeats reuse the same prepared cases and are repeated executions, not
independent samples. The complete comparison files preserve label agreement,
pairwise disagreement, means, uncertainty intervals, and all case-level data.

## Data integrity and comparability

| Dataset | `evals.csv` SHA-256 | Selection manifest SHA-256 | Dev / selection / final | Duplicates and prior overlap | Status |
| --- | --- | --- | --- | --- | --- |
| LEDGAR | `0cb73326d9de4277f5f709b5ebb5e13c5bf3ce4e9953633178cecd99436af3bf` | `497bb1664c7de6bb1c192f31bca99065752faaa6eb3ff4e6d43130fab11c7a70` | 500 / 1,000 / 500 | 0 | Pass |
| CFPB | `978383744e7110487d07ac33cc94e2566d07360671ee63cafa80987f525129ab` | `97549c946e15e6227dc0be83621a464c10ba341a257c05b1817dd015e5112d00` | 500 / 1,000 / 500 | 0 | Pass |
| SpamAssassin amended | `6e91f99f2cfb7afb895c82bf072518fb31bcc0dc9c3fc328d1484dd9cd907016` | `35d580043e7520f963abf0d2abdfb2246744e918f52a7e3cff93686eabea3247` | 500 / 1,000 / 500 | 0; both blocked IDs absent | Pass |

Comparability required identical case identifiers and bytes within each pair,
model identity, system prompt, runner, scorer, seed, runtime, permissions, and
frozen fallback contract. The final SpamAssassin audit verified 12 complete,
error-free promoted outputs and six passing paired comparisons.

## Paper-ready findings

### Methods paragraph

We evaluated fixed English and hybrid SOP packages on balanced subsets of
LEDGAR, CFPB, and SpamAssassin, using 500 development, 1,000 selection, and 500
reserved final-test cases per dataset after excluding previously opened IDs and
normalized content. Gemini 3.5 Flash Lite ran through OpenRouter's Google AI
Studio endpoint at low reasoning effort with eight workers. Each frozen package
was compared in three paired execution repeats using exact-match accuracy,
model calls, and model tokens. Selection required both accuracies of at least
80%, a paired accuracy lower bound of at least -2 percentage points, token
reduction of at least 5%, a positive paired token-reduction lower bound, and no
evaluation errors.

### Results paragraph

LEDGAR passed selection and, on the first 500-case final repeat, changed from
94.8% to 95.8% accuracy while reducing model calls from 500 to 130 and tokens
by 74.6%. CFPB was rejected on the 1,000-case selection split because hybrid
accuracy was 79.4% in the first repeat and remained below 80% in all repeats,
despite reducing calls from 1,000 to 788 and tokens by 23.4%. SpamAssassin
passed selection and, on the first 500-case final repeat, changed from 97.8% to
97.2% accuracy while reducing calls from 500 to 323 and tokens by 28.1%.

### Repeatability paragraph

Across the three fixed-case executions, LEDGAR final hybrid accuracy was 95.8%
in every repeat with 74.5-74.6% token reduction; CFPB selection hybrid accuracy
was 78.9-79.5% with 23.4-23.5% reduction and failed the same absolute gate each
time; SpamAssassin final hybrid accuracy was 97.0-97.4% with about 28.1%
reduction. These are repeated executions on the same cases rather than new
test samples.

### Limitations paragraph

The study evaluates one hosted model on balanced classification subsets with
fixed SOP packages. It does not independently measure autonomous discovery
reliability, full workflows, production distribution shift, dollar or energy
savings, or reduced output variability. CFPB did not reach final test.

## Verification and disposition

| Check | Result | Evidence |
| --- | --- | --- |
| Collection manifests verify | Pass | LEDGAR, CFPB, and SpamAssassin manifests; SpamAssassin 154/154 artifacts matched |
| Dataset audits pass | Pass | Per-dataset audits and two SpamAssassin amendment audits |
| Run-contract audits pass | Pass | Per-dataset collection audits |
| Statistical recomputation matches | Pass | Saved comparison JSON and selection gates |
| Repository verifier against new evidence | Not yet run | `reproduce/verify.py` still requires integration of the new manifests |
| Paper audit after integration | Not yet run | `paper/audit_paper.py` is not currently present |
| PDF rendered-page inspection | Not yet run | Manuscript has not yet been updated with these results |

**Disposition:** Evidence complete; paper integration pending.

**Supported conclusion:** For this frozen model and these fixed balanced
classification samples, the LEDGAR and SpamAssassin hybrid packages preserved
the preregistered quality margin while reducing model calls and tokens; the
CFPB package did not satisfy the absolute selection floor.

**Unsupported conclusions:** autonomous rule-discovery reliability, complete
business-workflow effectiveness, production readiness, and unmeasured cost,
energy, or variability claims.

## Remaining questions

None for interpreting the collected evidence. Manuscript integration and its
artifact audits remain separate required work before calling the paper current.
