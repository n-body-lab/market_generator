# Validation record

Implementation milestones were tested and committed sequentially:

1. Market models, seeded generation, local boundaries and codecs: 10 tests passed.
2. Unique-token walks, atomic execution, persistent progress and schedule budgets:
   28 tests passed before the milestone commit.
3. Exact search, infeasibility, incumbent/proof status and independent audit:
   41 tests passed before the milestone commit.
4. Difficulty, import validation, controlled experiments and documentation:
   48 tests passed on Python 3.12.14. Tested dependency versions are recorded in
   `requirements-tested.txt`; Python 3.11 compatibility is declared but was not
   exercised in this environment.

Additional validation:

- Editable package installation succeeded.
- Wheel build and installation into a separate target succeeded; generation and
  exact optimisation worked from the installed wheel.
- All easy/medium/hard example configurations generated and passed typed import
  validation; the small easy case proved optimal.
- Fifty seeds with three agents/tokens, modified prices, mixed tasks and alternating
  seller message costs passed generation and export/import checks. Search was
  deliberately capped at 300 states; no claim that every case proved optimal.
- Draft 2020-12 JSON Schema validated, and a generated export conformed to it.
- Experiments A/B/C ran seeds 0,1,2: nine routing, nine resource and three joint
  cases. Outputs are reproducible at `experiments/results/demo.json` after running
  the README command; generated results are ignored by Git.
- `git diff --check` passed.

Pytest reports a deprecation warning from the environment's externally installed
AnyIO pytest plugin; all package tests complete successfully.

## Engineering-review milestones

Each follow-up milestone ran the full suite before its commit: 52 tests after
controllability, 59 after decision fragility, 72 after optimisation improvements,
and 75 after experimental characterisation. The original 48 tests remain intact.
The final suite completed on Python 3.12.14; the external AnyIO warning remains.

The current wheel builds successfully. All six committed research exports pass
typed import/replay checks and JSON Schema validation. The controlled-study CLI
was also exercised end-to-end on two seeds after the full 100-seed measured runs.
Full measurements comprise 300 preset cases, 300 routing-depth requests, 100
incompatible-constraint controls, 300 paired-budget cases, 600 concentration/overlap
cases and 400 small reference/optimal cases. Failures, unknown classifications and
conditional denominators are retained in the reports and raw data.

## V0.3 targeted completion

The first requested fix passed 87 tests; the final suite passes 105, preserving
all 75 V0.2 cases. Decoy sensitivity and a two-agent, two-task fragile ordering
were verified exactly over seeds 0–4. Ledger corruption and intermediate
unaffordability are independently checked against a trusted anchor. Seven research
exports pass schema/import/strict replay. No expensive multi-seed scaling study
was repeated; details and remaining trust assumptions are in `final_validation.md`.
