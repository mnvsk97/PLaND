# Repository instructions

PLaND has two methodology skills: `generate-initial-version` and
`pland-evolver`. Keep experiment operations separate from those methodology
stages.

When the user asks to collect, run, resume, or package experimental data for
the paper, load `.codex/skills/pland-data-collection/SKILL.md` before acting.
The fresh paper collection uses exactly 500 development, 1,000 selection, and
500 final-test cases per dataset.

Do not invent or silently change an experiment plan, split, model, threshold,
candidate limit, or release gate. A request to start collection authorizes
execution of a plan whose exact contents the user has already reviewed; it does
not authorize creating or choosing a new plan. Preserve failed and successful
runs. Never open a reserved final-test split before its recorded selection gate
passes, and never put new numbers in the paper until the evidence manifest and
paper audit pass.
