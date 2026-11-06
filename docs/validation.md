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
