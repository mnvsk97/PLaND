# Confirmatory dataset proof index

The raw benchmark files are intentionally ignored. The JSON proof files below
are safe to check in: they contain counts, source and selection hashes,
exclusions, overlap checks, and repeatability results, but no complaint text,
contract clauses, email bodies, receipt fields, or document images.

| Dataset | Development | Validation | Untouched test | Pilot overlap | Proof status | Proof file |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| LEDGAR | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `proofs/ledgar-confirmatory.json` |
| CFPB complaints | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `proofs/cfpb-confirmatory.json` |
| SpamAssassin | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `proofs/spamassassin-confirmatory.json` |
| QS-OCR/Tobacco3482 | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `../experiments/document-classification/confirmatory-dataset-proof.json` |
| SROIE | 100 | 100 | 300 | 0 | Pass, repeated byte-identically | `../experiments/sroie-receipt-extraction/confirmatory-dataset-proof.json` |
| RVL-CDIP mirror | 100 | 100 | 369 | 0 | Pass; network repeat unavailable | `../experiments/rvl-cdip-document-classification/confirmatory-dataset-proof.json` |

The 1,000-case target is met for every retained source with enough immediately
available, usable, disjoint test cases. SROIE publishes 347 official test
receipts; removing pilot IDs, three cross-ID pilot-image duplicates, and exact image duplicates leaves 300. The
pinned RVL-CDIP mirror publishes 400 official test images; removing 16 pilot
images and 15 empty-OCR cases leaves 369. These shortfalls are reported rather
than filled by duplicates or by moving training data into the test split.

Every passing proof checks unique IDs, disjoint splits, missing files,
normalized or exact-content duplicates, expected-output leakage into runtime
inputs or paths, pilot overlap, source hashes, selection-manifest consistency,
and official split integrity where the source defines official splits.

Rebuild commands and source URLs are documented in `README.md`. Independent
repeat preparation was completed for every dataset except RVL-CDIP, whose
second download was rate-limited by the host. Its deterministic selector is
covered by unit tests, and the missing network repeat remains `null` in the
machine-readable proof rather than being reported as a pass.
