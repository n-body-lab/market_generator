# Difficulty validation: controlled market characterisation

## Protocol and interpretation

Executed on Python 3.12.14, NumPy 2.3.5, NetworkX 3.7. Each condition uses
100 explicit seeds, 0–99. Markets use fixed buyer execution-message cost 1 and
seller cost 0. Candidate routing depth is 3 unless a preset says otherwise;
retained candidates=3. Sampling attempts are capped at 100. Generated schedules
are replayed and independently audited. Exact benchmarking uses a 2,000-state cap;
action fragility uses 1,000 states per continuation search. No agent, discovery,
negotiation or learning process is simulated. These are full-information economic
and structural measurements, not demonstrations of collusion or misalignment.

Machine-readable raw measurements: `experiments/data/characterisation.json.gz`;
distributions and counts: `characterisation_summary.json`; concise tables:
`characterisation_summary.md`. Raw data contain configurations, individual seeds,
timings, requested/realised properties, bounds, gaps and classifications. Timing
is measured outside deterministic generation exports. Reproduce with:

```sh
python experiments/characterise.py --seeds 100
```

Values below are mean [empirical 10th percentile, 90th percentile], without
confidence intervals. All fractions use the definitions in `controllability.md`.
Accepted candidates satisfy every requested interval; rejection is conditional
sampling and can change other marginal distributions. Reported separation on a
constrained property is an acceptance guarantee, not an independent causal finding.

## Preset distributions

Six agents, twelve tokens, task counts 1–4. Easy uses prices 1–3, candidate depth
1 and relative leeway 1; medium prices 1–12, depth 2 and leeway .3; hard prices
1–30, depth 3, concentration .15, three targeted modifications and zero leeway.
Easy/medium concentration is .5. Requested indirect fractions are [0,.15],
[.2,.5] and [.6,1] respectively. Exact joint optimisation is disabled for this
structural distribution study; all reference schedules are verified feasible.

| Preset | Returned | Indirect fraction | Cheapest-path depth | Ownership HHI | Mean attempts | Candidate acceptance | Mean generation ms |
|---|---:|---|---|---|---:|---:|---:|
| easy | 100/100 | 0.037 [0.000, 0.111] | 1.037 [1.000, 1.111] | 0.421 [0.264, 0.597] | 1.52 | 0.658 | 5.31 |
| medium | 100/100 | 0.343 [0.200, 0.474] | 1.391 [1.214, 1.583] | 0.407 [0.264, 0.597] | 1.57 | 0.637 | 6.96 |
| hard | 100/100 | 0.744 [0.625, 0.889] | 1.969 [1.636, 2.417] | 0.685 [0.403, 1.000] | 1.74 | 0.575 | 10.36 |

All 300 preset requests succeeded within the attempt cap (zero observed market
failure rate). Candidate rejections are nonzero and are reported separately.
The routing distributions are distinguishable by design; HHI also changes, while
mean shared-demand fraction remains about .66 across presets. There is no claim
that these labels order strategic difficulty. Economic-family examples separately
characterise decision fragility rather than extrapolating it from these profiles.

## A — Routing depth, controlling generation parameters

Four agents, three tokens, task sizes 1–2, prices 1–20, concentration .5, relative
leeway .2, no price modifications, depth cap 3. Only the requested mean cheapest
unmet-dependency path-depth interval changes. All accepted instances are proved
optimal at the 2,000-state cap. Generation runtime includes screening and reference
validation; solver runtime is measured separately.

| Requested depth | Returned | Realised depth | Competitive alternative fraction | Reference transfers | Mean expanded states | Solver ms | Reference optimal |
|---|---:|---|---|---:|---:|---|---:|
| [1, 1] | 100/100 | 1.000 [1.000, 1.000] | 0.232 [0.000, 0.500] | 4.76 | 19.68 | 0.908 [0.166, 1.625] | 84/100 |
| [1.5, 2] | 100/100 | 1.661 [1.500, 2.000] | 0.269 [0.000, 0.667] | 6.00 | 37.14 | 1.457 [0.222, 2.761] | 69/100 |
| [2, 3] | 99/100 | 2.056 [2.000, 2.200] | 0.218 [0.000, 0.600] | 6.55 | 55.64 | 1.536 [0.193, 3.361] | 60/99 |

The highest-depth request exhausted its sampling cap on seed 35 (1% failure);
no violating market was returned. Across accepted markets, higher depth was
associated with more reference transfers and more expanded search states. This
is evidence within this conditional family, not a general complexity theorem.
Alternative-route availability was not monotone, and these small markets were
all tractable despite increased depth. Solver timings overlap substantially.

Negative control: keeping two dependency-targeted price modifications while
requesting mean depth exactly one failed on all 100 seeds after 100 attempts.
The last targeted modification ensures at least one unmet dependency has a cheaper
indirect alternative, so this combination conflicts structurally. We retain these
results in `A_conflict`, rather than relaxing the constraint or counting a bad
sample as success. The primary comparison holds modifications at zero for all
three depth conditions.

## B — Paired budget scarcity

For every seed, use the exact same fragile-family market (three agents, required
token initially at agent 0, decoy at agent 2, agent 1 is the sole demander).
Uniform off-diagonal price p is seeded in [2,5]. Starting reference balances are
(0,p+1,0); absolute leeway adds the same amount to each agent. Ownership, prices,
tasks, provenance and reference actions are unchanged within each seed pair.
Every action classification in this study completed exactly.

| Absolute leeway | Fragility F | Affordable actions | Preserving actions | First-completing sequences within 3 transfers |
|---|---|---|---|---|
| 0 | 0.500 [0.500, 0.500] | 2.000 [2.000, 2.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| 1 | 0.000 [0.000, 0.000] | 2.000 [2.000, 2.000] | 2.000 [2.000, 2.000] | 2.000 [2.000, 2.000] |
| 4 | 0.000 [0.000, 0.000] | 2.780 [2.000, 4.000] | 2.780 [2.000, 4.000] | 6.290 [2.000, 13.000] |

At zero leeway a decoy purchase destroys feasibility; one additional credit per
agent removes this risk in every pair. Every market still has a verified complete
schedule. More leeway can increase affordable actions and short alternative
schedules. Sequence counts stop at first completion and are horizon-limited;
they do not count arbitrarily long cycles. Raw records include agents able to
send one message, one-credit depletion sensitivity, and action-specific alternative
buyer outcomes. Communication affordability is liquidity, not discovery success.

The independently hand-verified robust/fragile/highly-constrained families have
F=0, 1/2 and 5/6 over the five seeded test prices, respectively. They isolate the
mechanism: after a bad purchase the seller receives p but needs p+1 to buy anything.
All three example benchmarks have proven optimum schedules even though different
first actions have different consequences. Financed reference purchases are also
reported via a counterfactual removing earlier sale proceeds; this is a schedule
measurement rather than a global economic necessity claim.

## C — Ownership concentration and shared demand

Three agents, three tokens, tasks 1–2, prices 1–12, no modifications, zero budget
leeway. Vary Dirichlet concentration .1, 1 and 5, crossed with low shared-demand
fraction [0,.5] and high [.8,1]. There are 100 seeds per cell; all 600 requests
succeeded within 100 attempts. Constraints apply to realised overlap, not a task
sampling label. All reference-quality searches were proved at the cap.

| Concentration / overlap | Ownership HHI | Shared-demand fraction | Shared intermediaries | Fragility F | F available |
|---|---|---|---|---|---:|
| (0.1, [0, 0.5]) | 0.904 [0.556, 1.000] | 0.435 [0.000, 0.500] | 0.080 [0.000, 0.000] | 0.243 [0.000, 0.500] | 100/100 |
| (0.1, [0.8, 1.0]) | 0.893 [0.556, 1.000] | 0.877 [0.800, 1.000] | 0.150 [0.000, 1.000] | 0.133 [0.000, 0.500] | 100/100 |
| (1.0, [0, 0.5]) | 0.684 [0.556, 1.000] | 0.440 [0.000, 0.500] | 0.070 [0.000, 0.000] | 0.261 [0.000, 0.667] | 100/100 |
| (1.0, [0.8, 1.0]) | 0.671 [0.556, 1.000] | 0.899 [0.800, 1.000] | 0.100 [0.000, 0.000] | 0.152 [0.000, 0.500] | 100/100 |
| (5.0, [0, 0.5]) | 0.591 [0.333, 1.000] | 0.435 [0.000, 0.500] | 0.040 [0.000, 0.000] | 0.243 [0.000, 0.600] | 99/100 |
| (5.0, [0.8, 1.0]) | 0.584 [0.333, 1.000] | 0.900 [0.800, 1.000] | 0.040 [0.000, 0.000] | 0.162 [0.000, 0.500] | 99/100 |

Concentration changes realised ownership HHI as intended. It did **not** show a
monotone increase in fragility: low-overlap means were roughly .24–.26 across
concentrations. High overlap instead had lower average fragility in this sample.
More shared demand does not necessarily imply greater economic danger. Shared
intermediary counts are low and do not establish unavoidable bottlenecks on a
fully connected graph. The raw route-branching/intermediary and overlap metrics
are retained rather than collapsed into a competition score.

598/600 fragility measurements were available. Seed 49 at concentration 5/low
overlap had no affordable actions; seed 51 at concentration 5/high overlap retained
an unclassified action at the search cap. Neither was imputed as zero. Selection
on overlap changes ownership/task correlations, and every structure gets its own
reference-derived budget. This is descriptive evidence, not an isolated causal
estimate of concentration's effect with all resources fixed.

## D — Reference routes versus exact joint optimum

Task counts 1–min(tokens,3), default prices/concentration, relative leeway .2,
no structural conditioning, 100 seeds per size. All 400 instances were proved
optimal at the 2,000-state cap, but this small-instance family does not justify
claims about arbitrary larger markets.

| Agents/tokens | Proven optima | Reference already optimal | Solver seconds |
|---|---:|---:|---|
| (2, 2) | 100/100 | 100/100 | 0.000 [0.000, 0.000] |
| (3, 2) | 100/100 | 96/100 | 0.000 [0.000, 0.001] |
| (3, 3) | 100/100 | 94/100 | 0.000 [0.000, 0.001] |
| (4, 3) | 100/100 | 73/100 | 0.004 [0.000, 0.010] |

The reference is strictly suboptimal on 4%, 6% and 27% of sampled 3/2, 3/3 and
4/3 cases respectively. Raw records preserve all three objective components,
proven optimum costs, component differences and lexicographic excess. The retained
hand example in `test_independent_cost_optima_are_not_joint_lexicographic_optimum`
has reference (4,4,4) and optimum (2,2,16): accepting higher gross payments is right
when it saves messages/transfers. A componentwise weighted score would misstate
that comparison. See `optimality_benchmarks.md` for larger unresolved gaps, baseline
profiles, ablation, and limits; do not infer standard-size optimality from these
small-instance successes.

## Observability and remaining research limits

All structural, resource, benchmark and exact-fragility measurements require the
generator's full information. An agent receives only its own local view; the
number of messages needed to learn remote inventories, tasks or prices requires
an actual communication protocol and traces. Existing discovery quantities stay
labelled proxies. Execution costs are measured separately from hypothetical
exploration costs, and M=X under the default policy.

These studies demonstrate controllable conditional distributions, exact economic
choice sensitivity on small markets, and a benchmark against feasible/proven
solutions. They do not establish rationality, irrationality, collusion or alignment
outcomes for autonomous agents. They also do not validate a single universal
notion of difficulty. Seed variation, sampling bias, integer price granularity,
reference-dependent endowments and search/horizon caps remain material limitations.
No heavy optimiser, agent policy or distributed infrastructure was introduced.
