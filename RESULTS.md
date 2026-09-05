# Reported results

This page is a navigation aid. The paper remains the authoritative narrative;
the linked experiment directories contain the machine-readable evidence.

## Original confirmatory study

| Workflow and split | Quality, NL to hybrid | Tokens, NL to hybrid | Decision |
|---|---:|---:|---|
| LEDGAR validation (100) | 92.0% to 93.0% accuracy | 37,147 to 21,104 | Pass; test released |
| LEDGAR test (1,000) | 93.5% to 92.7% accuracy | 376,088 to 225,573 | Pass |
| CFPB validation (100) | 79.0% to 72.0% accuracy | 60,514 to 35,247 | Reject; test closed |
| SpamAssassin validation (100) | 90.0% to 86.0% accuracy | 238,077 to 228,359 | Reject; test closed |
| QS-OCR/Tobacco validation (100) | 70.0% to not run | 1,082,556 to not run | Baseline nonviable |
| SROIE LiteParse validation (100) | 0.344 field F1 to not run | 49,768 to not run | Baseline nonviable |
| RVL mirror validation (100) | 50.0% to not run | 1,072,199 to not run | Baseline nonviable |

## Three-run optimized replications

| Workflow and split | Mean accuracy, NL to hybrid | Mean tokens, NL to hybrid | Decision |
|---|---:|---:|---|
| LEDGAR test (1,000) | 93.7% to 92.9% | 376,090 to 225,575.33 | Pass in 3/3 runs |
| CFPB validation (100) | 78.0% to 71.0% | 58,372 to 33,120 | Reject in 3/3 runs |
| SpamAssassin validation (100) | 88.0% to 85.0% | 188,384 to 178,880.67 | Reject in 3/3 runs |

## Fresh quality-first validation

| Dataset | Accuracy, NL to candidate | Difference and 95% interval | Outcome |
|---|---:|---:|---|
| LEDGAR | 93.6% to 92.8% | -0.8 points [-1.6, -0.2] | Reject |
| CFPB | 74.8% to 73.8% | -1.0 points [-2.4, +0.2] | Reject |
| SpamAssassin | 90.2% to 89.0% | -1.2 points [-2.2, -0.4] | Reject |

No quality-first test split was opened.

## Evidence locations

- [`experiments/ledgar-text-classification/`](experiments/ledgar-text-classification/)
- [`experiments/cfpb-text-classification/`](experiments/cfpb-text-classification/)
- [`experiments/spamassassin-email-classification/`](experiments/spamassassin-email-classification/)
- [`experiments/document-classification/`](experiments/document-classification/)
- [`experiments/sroie-receipt-extraction/`](experiments/sroie-receipt-extraction/)
- [`experiments/rvl-cdip-document-classification/`](experiments/rvl-cdip-document-classification/)
- [`experiments/variance-study/summary.json`](experiments/variance-study/summary.json)
- [`experiments/quality-first-replications/summary.json`](experiments/quality-first-replications/summary.json)

Raw licensed or sensitive records are not committed. Result JSON, comparisons,
safe traces, manifests, hashes, and the scripts that generated them are.
