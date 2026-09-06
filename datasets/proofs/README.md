# Confirmatory dataset proof index

The raw benchmark files are intentionally ignored. The JSON proof files below
are safe to check in: they contain counts, source and selection hashes,
exclusions, overlap checks, and repeatability results, but no complaint text,
contract clauses, email bodies, receipt fields, or document images.

| Dataset | Development | Validation | Untouched test | Pilot overlap | Proof status | Proof file |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| LEDGAR | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `ledgar-confirmatory.json` |
| CFPB complaints | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `cfpb-confirmatory.json` |
| SpamAssassin | 100 | 100 | 1,000 | 0 | Pass, repeated byte-identically | `spamassassin-confirmatory.json` |

Every passing proof checks unique IDs, disjoint splits, missing files,
normalized or exact-content duplicates, expected-output leakage into runtime
inputs or paths, pilot overlap, source hashes, selection-manifest consistency,
and official split integrity where the source defines official splits.

Rebuild commands and source URLs are documented in [`../README.md`](../README.md).
