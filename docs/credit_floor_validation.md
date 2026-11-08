# Minimum initial credit floor

## Targeted implementation

`MarketConfig.minimum_initial_credits` defaults to 0. It must be a nonnegative
Python integer; negative values, floats and booleans are rejected. The existing
reference-budget calculation and leeway functions are unchanged. Endowments are:

`initial_i = max(minimum_initial_credits, reference_i + leeway_i)`

Relative leeway remains `ceil(lambda_i * reference_i)`; absolute leeway remains
`ceil(lambda_i)`. Scalar and per-agent leeway are retained. The floor is applied
**after** leeway and only to initial endowments. It neither modifies reference
requirements nor adds a floor amount to every existing budget. For example,
reference (0,5,10), relative leeway .2 and floor 3 produces (3,6,12).

The default of zero preserves prior behaviour. A frozen pre-change seeded export
is compared in full, excluding only the new config field and `credit_allocation`
metadata group. That test covers prices, tasks, ownership, paths, schedules,
budgets, difficulty, solver results and the rest of the metadata.

### Metadata

Every new result records `metadata.credit_allocation` with:

- `reference_budgets`: unchanged fixed-schedule minimum endowments.
- `initial_credits_before_floor`: reference plus existing leeway.
- `initial_credits`: actual initial allocation after flooring.
- `minimum_initial_credits`: applied floor.
- `zero_credit_agents`: count after the floor.
- `agents_increased_by_floor`: agents whose post-leeway allocation was raised.
- `additional_credits_from_floor`: aggregate increase over the unfloored allocation.
- `zero_credit_agents_with_unfinished_tasks`: post-floor zeros with unmet requirements.
- `zero_credit_agents_before_floor_with_unfinished_tasks`: the corresponding
  pre-floor count, to distinguish relieved bottlenecks from already completed tasks.

Typed import treats a missing historical floor as zero and validates the actual
initial balances against the exact floored formula. Reference budgets continue to
be independently recomputed and checked. The schema field is optional for old
files, with nonnegative integer type and default zero. Historical metadata may lack
the new group and is retained; balances, not metadata assertions, establish feasibility.

## Reproducible 100-seed paired study

Command: `python experiments/credit_floor_comparison.py --seeds 100`.
The default six-agent/twelve-token configuration is used, with seeds 0–99, relative
leeway .2, and floors 0,1,3,5. Every other parameter stays at its default, including
the exact-search state cap of 20,000. This is 400 separately generated markets.

For each seed, equality checks cover the market, price matrix, ownership, tasks,
candidates, token routes, initial progress/histories, reference budgets, compact
reference transfers and explicit OFFER/BUY schedule. They are identical across
floors. The raw records retain a paired structure/reference hash, full config,
credits, counts, reference costs, optimisation termination status and runtime.
Every reference is replayed through the existing economic/protocol verifier.

Market percentages use 100 markets per condition. Agent percentages use **all
600 agents** per condition; the unfinished-task percentage is not conditional on
being unfinished. Added credits are measured against the same seed at floor zero,
after leeway, not against the raw reference budgets.

| Floor | Markets with zero-credit agents | Zero-credit agents | Zero-credit agents with unfinished tasks | Mean total credits | Median total credits | Mean added credits | Reference feasible |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 90.0% | 22.5% | 16.0% | 67.93 | 65.50 | 0.00 | 100% |
| 1 | 0.0% | 0.0% | 0.0% | 69.28 | 67.50 | 1.35 | 100% |
| 3 | 0.0% | 0.0% | 0.0% | 72.12 | 70.00 | 4.19 | 100% |
| 5 | 0.0% | 0.0% | 0.0% | 75.74 | 73.50 | 7.81 | 100% |

Machine-readable measurements: `experiments/data/credit_floor_comparison.json.gz`.
A concise table is also saved as `credit_floor_comparison.md`. Standard-library
gzip keeps the raw record small; seed configurations and outputs are reproducible,
while measured wall-clock durations vary across runs.

## Validation and scope

The complete suite passes **152 tests**, including all previous 135 and 17 focused
floor cases: examples above, absolute/vector leeway, invalid config values,
zero-floor identity, historical/positive-floor JSON, import corruption, metadata,
paired structures and monotone reference feasibility. All eight historical example
exports pass schema/import with floor zero. A positive-floor export also passes
schema and typed round-trip checks. The comparison CLI was smoke-tested separately.

For a fixed schedule, adding nonnegative starting credits adds the same constant
to every later balance of that agent because the scheduled payments/fees do not
change. Thus raising the floor cannot make that reference infeasible. All 400
measured references remained feasible. No globally minimal endowment or new
optimality theorem is claimed; the optimiser and objective were not changed.

A positive floor funds initial communication but does not ensure discoveries,
seller consent, affordable eventual purchases, or successful autonomous coordination.
It increases total resource supply and may change feasible alternatives, difficulty
resource measurements and the optimum/proof status. The default experiment has
no structural acceptance constraints. If researchers condition sampling on resource
metrics such as limited-slack fraction, a changed floor can change which candidates
are accepted; use a supplied fixed market for strictly paired resource studies.
The usual sequential/static-price/cooperative-reference limitations remain.

### Usage and changed files

```python
from hivemarket_generator import MarketConfig, generate_market

result = generate_market(MarketConfig(minimum_initial_credits=3, seed=42))
assert min(result.initial_state.balances) >= 3
print(result.reference_budgets)
print(result.metadata['credit_allocation'])
```

Runtime changes are confined to `config.py`, `credits.py`, `generation.py` and
`serialization.py`, plus the optional config property in `docs/market.schema.json`.
Tests are in `tests/test_credit_floor.py`. The paired experiment, its recorded
results, README and this report accompany the change. No reference-budget logic,
OFFER/BUY rule, graph/routing/allocation/task algorithm, optimiser, liquidity check
or main exploration repository was changed.
