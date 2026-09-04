# Frozen final-submission inputs

These two PDFs are the minimal source package for reproducing the approved
nine-page submission layout:

- `reviewed-base.pdf` is the reviewed nine-page manuscript received from Asit.
- `replacement-page-2.pdf` is the approved page 2 containing the revised
  LEDGAR natural-language, hybrid, and graph-based SOP figure.

`../build_final_submission.py` verifies both SHA-256 hashes, retains pages 1
and 3-9 from the reviewed base, inserts the approved replacement page, and
writes `output/paper/PLAND_SUBMISSION_READY_FINAL.pdf`. With the root locked
environment, repeated builds are byte-identical.

The replacement page is retained because the reviewed typesetting source was
provided as PDF rather than as an editable DOCX or LaTeX project. The editable
repository manuscript and figures remain under `paper/`.
