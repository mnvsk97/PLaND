# Paper integration

The editable manuscript source is `paper/PLaND.md`. Existing result extraction
in `paper/audit_paper.py` points to the historical confirmatory and variance
artifacts; new evidence is not integrated merely because collection completed.

After the collection reaches a terminal state:

1. Generate and verify the collection manifest.
2. Add a paper audit path that recomputes every proposed number from the new
   saved case-level outputs and comparisons. Do not type calculated metrics into
   the manuscript by hand.
3. Update the manuscript's methods, results, limitations, and evidence pointers
   to describe the stage actually measured. Do not rename selection results as
   final-test results.
   Updating sample sizes and observed numbers from the fresh evidence is
   expected; do not add a claim that autonomous discovery reliability was
   independently evaluated.
4. Rebuild Word, HTML, and PDF using the repository's existing builders.
5. Run `python paper/audit_paper.py --artifacts` and
   `python reproduce/verify.py`, updated to include the new manifest.
6. Inspect every rendered PDF page before claiming the paper is current.

Keep the previous evidence immutable. New evidence should live in a new,
study-specific results directory with its own manifest and command ledger.
