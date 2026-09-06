# cfpb fresh collection evidence

The approved split is 500 development / 1,000 selection / 500 final test.
Read `results/collection-audit.json` and the recorded selection release before
interpreting any outcome. Missing final-test files mean the test was unopened.
The run JSON contains safe classification outputs and model response metadata;
licensed source documents and expected-answer CSVs remain in the local data
directory and are represented here by hashes and provenance.

The archived commands retain their original absolute paths. Exact reruns need
the locked source bytes and path resolution to a new checkout. The `generated`
package is the initial skill output; `chosen-baseline.json` (or `baseline-01` when no refinement was needed) identifies the English package used
by the fixed request harness in `implementation/deepagent_execution.py`.
All model-mediated work uses Qwen through `create_deep_agent`; direct command
routes use the frozen classifier and invoke that identical English fallback
on abstention. No result is an autonomous rule-discovery reliability estimate.
