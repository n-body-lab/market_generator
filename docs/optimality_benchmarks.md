# Exact optimisation benchmarks

**Historical-model note:** this report predates the revised OFFER/BUY rules.
Default one-buyer-message transfer budgets remain valid as just-in-time OFFER/BUY
plans. Nonstandard seller-fee examples require explicit legacy mode and are not
current-rule evidence. See [current protocol](offer_protocol.md).

Measurements on Python 3.12.14, NumPy 2.3.5 and NetworkX 3.7 in this cloud worker.
Five seeds (0–4) per size, task sizes uniform in [1,min(tokens,3)], other
parameters at defaults, automatic search disabled during sampling. Each solver
receives the same verified reference incumbent and a 5,000 label/expansion cap.
Times are wall-clock means in seconds, not portable performance guarantees.

| Agents/tokens | Legacy proofs | Compact uniform-cost proofs | A* proofs | Legacy seconds | Compact seconds | A* seconds |
|---|---:|---:|---:|---:|---:|---:|
| 2/2 | 5/5 | 5/5 | 5/5 | 0.00016 | 0.00010 | 0.00007 |
| 3/2 | 5/5 | 5/5 | 5/5 | 0.00048 | 0.00044 | 0.00021 |
| 3/3 | 5/5 | 5/5 | 5/5 | 0.01514 | 0.00471 | 0.00015 |
| 4/3 | 5/5 | 5/5 | 5/5 | 0.09571 | 0.03430 | 0.00330 |
| 4/4 | 3/5 | 3/5 | 5/5 | 0.10086 | 0.04129 | 0.00208 |
| 6/12 | 0/5 | 0/5 | 1/5 | 0.11212 | 0.03774 | 0.11930 |

Of 26 A*-proven cases, 19 reference schedules were already optimal. This fraction
is conditioned on tractability; it is not an unbiased quality estimate for all
generated markets. All unresolved runs retain a verified incumbent, lower bound,
and first-unresolved-coordinate gap in `solver_improved.json`. Componentwise cost
differences can be negative even when a reference is lexicographically worse.

## Diagnosis and correction

The original profile (`experiments/data/solver_baseline_profile.txt`) records 4,368
`execute` calls in a 2,000-label default-size run. Event/history construction,
repeated objective computation and tuple hashing consume substantial time;
branching over token/buyer pairs drives label growth. Copy-free search bitmasks
and path links remove provenance construction from speculative transitions. All
returned witnesses still pass the original enforcement/replay validator.

An admissible, consistent heuristic counts K unmet agent-token requirements:
each transfer satisfies at most one, so remaining transactions >=K; execution
messages >=qK under fixed q messages per transfer. Gross payments are at least
the sum, over unmet requirements, of the buyer's minimum incoming price. Adding
these coordinatewise bounds gives a valid lexicographic lower bound. A* prioritises
this bound and prunes branches that cannot beat the incumbent. No ownership,
liquidity or task constraint is relaxed in actual successor generation.

The original uniform-cost mode remains available as `use_lower_bound=False` for
ablation. Exact search is tested against it and independent bounded enumeration,
including zero-message pricing. `time_limit_seconds` and state/label caps produce
`feasible` with a witness or `unknown` without one, never unsupported infeasibility.
The returned lower bound includes unfinished siblings when a label cap fires.
An optimality gap is reported at the first differing lexicographic coordinate;
there is no Euclidean or weighted-sum gap.

## Practical conclusions and limitations

All sampled cases up to 4 agents/4 tokens were proved by A* under this small cap.
Only one of five 6-agent/12-token cases was proved: the bound helps some instances
but adds overhead on others. Large-instance optimality remains unresolved.
Sampling just five seeds per size establishes a practical pilot, not a universal
tractability boundary. Resource magnitudes, shared demand and minimum path costs
can change performance sharply at fixed dimensions.

Automatic search now covers up to 6 agents/12 tokens with the existing default
20,000-state cap, so standard markets receive a genuine bounded optimisation
attempt rather than a dimension-based skip. The canonical generation `status` is
`optimal` or `feasible`; the older `optimality_status` retains `not_run` and
`limit_reached` as termination metadata for compatibility. `OptimizationResult.conclusion`
provides `optimal`, `feasible`, `infeasible`, or `unknown`; its legacy `status` is
preserved. No heavy solver dependency was justified or introduced.

Raw data retain every seed, cap, time, incumbent, bound, gap and reference quality.
Reproduce the current solver ablation with:

```sh
python experiments/benchmark_solver.py --seeds 5 --state-limit 5000
```

The historical baseline was measured at commit `0c51105` before replacing its
solver. Historical timings vary on repetition. Larger multi-seed research studies
and reference-quality measurements are in `docs/difficulty_validation.md`.
