# HIVEMARKET Market Generator

A standalone Python 3.11+ research package for reproducible information markets.
It generates unique transferable tokens, overlapping tasks, directed prices,
feasible benchmark schedules and sufficient budgets. Small markets can carry a
proof of lexicographic optimality. It implements no participating agents.

## Install and run

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python examples/generate.py
python experiments/run.py --seeds 0 1 2 --output experiments/results/demo.json
```

```python
from hivemarket_generator import MarketConfig, generate_market, dumps, loads, decode_result

config = MarketConfig(
    n_agents=6, n_tokens=12, max_candidate_depth=3,
    ownership_concentration=0.5, task_dependency_range=(1, 4),
    budget_leeway=0.2, seed=42,
)
result = generate_market(config)
assert result.feasibility_status == "verified"
print(result.reference_solution.objective)  # OFFER expenditure, transfers, gross payments
with open("market.json", "w") as f:
    f.write(dumps(result))
restored = decode_result(loads(dumps(result)))
```

`initial_state`, `reference_solution`, `reference_budgets`, `token_routes`,
`candidates`, `best_solution`, `optimal_solution`, `difficulty`, `metadata`,
`seed`, and `config` are explicit result fields. All results export to versioned
JSON. `prepare_market(market, config)` benchmarks a supplied structure with the
same scheduling, credit allocation, validation, and optimisation pipeline.

## Mechanics and information boundaries

`P[buyer][seller]` is the token price. Off-diagonal prices are positive finite
**integers**, diagonal zero. Uniform inclusive and rounded triangular price
distributions are supported. Set `asymmetric_prices=False` for initially symmetric
prices; subsequent directed price modifications can break that symmetry.
All trades remain available. Price modification may exceed the initial price
range to make an indirect path cheaper.

Exactly one current owner exists per token. `State.histories[t]` starts with its
initial owner and appends each buyer, including repeat visits. `State.events`
contains ordered immutable transfer records. Provenance is verified by replay;
optional signature fields reserve an integration point without claiming
cryptographic authenticity. Frozen tuples/dataclasses prevent accidental in-place
mutation; a caller can construct a forged state, which validators must reject.
Tasks retain progress after tokens are sold. Capacity is unlimited.

Agents should receive `local_view(market, state, agent)`, not a `GenerationResult`.
A view contains only the agent's balance, inventory, task, progress, incident
prices, agent ID and total agent count. Full models and benchmarks belong to the
generator. Python objects alone are not a security sandbox.

Current generation uses **OFFER / WITHDRAW / BUY**:

- OFFER costs the buyer one credit immediately and creates a persistent, nonbinding
  demand signal. The target need not own the token. No credits or token are reserved.
- WITHDRAW closes the buyer's active offer for free and refunds nothing.
- BUY requires an active associated offer, the named seller's current ownership,
  and enough buyer credits for `P[buyer][seller]`. Atomic settlement transfers the
  price with **no additional communication tax**, closing only that offer.

Other offers survive purchases and seller ownership changes, including loss and
reacquisition of a token. Completed agents can keep trading. Reference schedules
issue exactly one OFFER immediately before each BUY; no extra OFFER is needed.

```python
from hivemarket_generator import verify_protocol_solution, protocol_summary

plan = result.reference_solution.protocol_actions  # explicit OFFER/BUY records
final = verify_protocol_solution(result.market, result.initial_state, result.reference_solution)
print(protocol_summary(result.market, result.initial_state, final))
```

[Protocol and accounting details](docs/offer_protocol.md) explain standing offers,
free withdrawals, serialized plans and the sequential feasibility assumptions.
`OfferState` keeps the explicit offer ledger and untaxed settlement events.
Its `offer_messages` counts OFFER expenditure. `validate_offer_execution` checks
that ledger independently from a trusted initial snapshot.

For compatibility, `Solution.actions` and `execute(Transfer)` retain the compact
reference projection: at the default policy each step represents one just-in-time
OFFER plus BUY. The compact Event's buyer message count allocates its OFFER cost;
it is not an extra BUY charge. Use `apply_protocol`/`replay_protocol` when modelling
persistent offers. Do not treat an explicit `OfferState.economy` as the compact
fixed-message ledger; reconcile the complete OfferState with its protocol validator.

Nonstandard `buyer_messages`/`seller_messages` require explicit
`communication_protocol="legacy_fixed_messages"`. They exist only to reproduce
historical experiments and are labelled as such in metadata; they are not current
game rules. Old seller-fee fragility examples do not establish current-rule fragility.
No full discovery protocol, broker, asynchronous escrow service or agent runtime
is implemented.

## Algorithm and budgets

See [generation algorithm](docs/algorithm.md) and [mathematical specification](docs/mathematics.md).
Generation uses one NumPy RNG. Ownership is a Dirichlet categorical allocation
(equivalently Dirichlet–multinomial counts with random token labels); small
concentration tends toward concentration, not a guarantee on each sample.
Tasks sample heterogeneous counts and route-biased subsets, allowing shared
and initially satisfied requirements. Different target path lengths are sampled
within each market. No demand count or difficulty label guarantees a realised
metric.

Generation accepts measured constraints, for example:

```python
config = MarketConfig(
    target_indirect_dependency_fraction=0.5,  # minimum cheapest-payment indirect fraction
    structural_constraints={"shared_demand_fraction": (0.5, 1.0)},
    generation_attempt_limit=100,
    price_modifications=3,
    seed=42,
)
result = generate_market(config)  # raises GenerationFailure on exhausted attempts
print(result.metadata["requested_properties"])
print(result.metadata["realised_properties"])
assert result.metadata["constraints_satisfied"]
```

See [constraint definitions](docs/controllability.md): cheapest-payment routing
is distinct from the globally optimal lexicographic schedule. Direct trades remain
possible. Successful generation never silently relaxes requested intervals.

Candidate walks retain a configurable number of cheap alternatives up to
`max_candidate_depth` edges. Full token journeys have no such depth cap.
Independent token walks minimise gross payments ignoring credit constraints
(exact up to eight unmet demanders, nearest-demand heuristic beyond that).
A round-robin interleaving preserves token ownership. Componentwise minimum
initial budgets are computed **for that ordering**, including message expenditure
and receipts from earlier sales, then augmented with leeway. Replay and a separate
arithmetic auditor verify the complete schedule. Because budgets are allocated
after the schedule, generation needs no infeasible-budget retries. This constructs
a feasible benchmark; it does not prescribe agent behaviour or find globally
minimum initial endowments.

`budget_leeway=0.2` with `leeway_mode="relative"` adds `ceil(0.2*reference_budget)`.
Absolute mode adds `ceil(leeway)` credits. A tuple sets per-agent leeway.
A zero reference balance receives zero relative leeway; use absolute mode to
fund such agents. `MarketConfig.preset("easy"|"medium"|"hard", **overrides)` and
[example configurations](examples) expose concrete parameters. Compare actual
metrics rather than assuming monotonic difficulty between random draws.

## Optimality and scope

The objective is lexicographic `(OFFER communication expenditure, token transfers, gross trade
payments)`. In the reference normal form each transfer has one OFFER, so the
first two coordinates are redundant. Starting from no offers, unused offers can
be omitted and each used OFFER postponed to just before its BUY without reducing
feasibility. This justifies the existing compact exact search for the revised rules.
It does not prove anything about discovery costs or optimisation from pending offers.
Discovery communication has **no** claimed minimum here. A cheap indirect route
can lose to an expensive direct trade on the primary objective.

`solve_exact(market, initial_state, state_limit=20000, incumbent=None)` searches
all legal transfers on the complete graph, with immutable ownership, permanent
progress, integer balances and one-credit OFFER costs in this normal form. The state space is
finite. Costs are compared exactly; there are no numerical tolerances.

- `optimal`: a feasible globally optimal schedule is proven under these rules.
- `infeasible`: exhaustive search proves no complete schedule for those budgets.
- `limit_reached`: no proof; `best_solution` is a verified incumbent if available.
- Generation's `not_run`: market exceeds configured automatic-search dimensions
  (defaults: six agents and twelve tokens), or exact search is disabled.

The canonical `result.status` is `optimal` or `feasible` for generated markets.
`solve_exact(...).conclusion` is one of `optimal`, `feasible`, `infeasible`, `unknown`.
The older status fields above remain available as search termination metadata.
Search exports a lower bound, incumbent, and first-unresolved-coordinate gap;
`metadata["reference_quality"]` compares references with proven optima. See
[solver benchmarks](docs/optimality_benchmarks.md).

Feasibility and optimality are separate. `optimal_solution` is populated only
with proof; `best_solution` includes the feasible reference when proof is absent.
Search caps both expanded states and discovered labels; an optional
`time_limit_seconds` also limits search. Efficient scaling is not promised. Large credit balances can enlarge the search
space substantially, even for few tokens. The cap can conservatively interrupt
before completing a proof. Baseline zero-length complete tasks are optimal too.
No theorem about unknown future communication protocols is implied.

## Difficulty analysis

`result.difficulty` has four groups, with no arbitrary scalar score:

- Routing: first-visit hops per requirement, whole-token journey lengths, retained
  alternatives, branching, revisit/cycle closures, shared intermediary route counts.
- Discovery proxies: unknown location and route-price occurrences, plausible
  intermediaries, a naive independent-location search-space estimate. These are
  not measured discovery costs; unique-token/shared-demand correlations are ignored
  by that search-space estimate.
- Resources: budgets, schedule requirements, absolute/relative slack, a configurable
  limited-slack fraction, execution messages, and gross payments. Undefined relative
  slack at zero reference is `null` with absolute slack reported separately.
- Strategic proxies: shared demands, task overlap, route participation and the
  effect of deleting each reference transaction **without replanning**. Intermediary
  dependence describes the benchmark, not unavoidable vertices of a complete graph.

Optional `analyse_fragility(market, state, state_limit=5000)` examines each affordable
first transfer, classifies its continuation as feasible, impossible or unclassified,
and reports objective differences when both optima are proven. It also tests one
credit of exploratory expenditure per funded agent. It can be expensive; it is
not run during ordinary generation.

`decision_fragility` is the exact fraction of affordable transfers that destroy
completion feasibility. It is null if any action remains unclassified; no-action
states are reported separately. See [economic families](docs/decision_fragility.md).
The reproducible examples `economic_family("robust"|"fragile"|"highly_constrained")`
prove fragility 0, 1/2 and 5/6 without modelling agent behaviour.

## Research validation

[Difficulty validation](docs/difficulty_validation.md) reports 100-seed studies of
preset distributions, routing depth, paired budget leeway, ownership/overlap, and
reference versus proven optima, including negative and unresolved outcomes.

```sh
python experiments/characterise.py --seeds 100
python experiments/benchmark_solver.py --seeds 5 --state-limit 5000
python examples/research_markets.py
```

The characterisation exports compressed raw JSON and a JSON distribution summary
in `experiments/data/`; committed measurements and [example exports](examples/markets)
are included. Timings vary across machines. Full-market structural metrics and
exact feasibility are generator-side observations. Actual discovery messages,
what agents know over time, negotiation and learned behaviour require downstream
communication traces and are not measured here. Execution and exploratory message
costs stay separate; the default objective still has messages equal to transfers.

## Reproducible experiments

`experiments/run.py` runs controlled constructed market families over multiple
seeds, exporting assumptions, parameters, counts and proof statuses to JSON:

A. Directed cheap chains with increasing demand distance show longer token walks;
   mixed/shared demands remain present. Alternative counts are explicitly capped.
B. A fixed two-token swap varies only absolute budget leeway. Both transaction
   orders are tested: extra credit enables the initially unaffordable order.
C. Independent least-payment token walks are compared with exact joint schedules.
   The joint optimum uses fewer transfers/messages while accepting higher gross
   payments, demonstrating why independent routing is not the joint benchmark.

These are demonstrations of mechanisms, not statistical validation of a universal
difficulty scale. Generated random markets can be studied separately using the
same metrics. No RL or LLM agents are involved.

## Format and validation

See [format contract](docs/format.md) and [JSON Schema](docs/market.schema.json).
`decode_market` and `decode_state` validate structural invariants. `decode_result`
replays solutions with both validators; exported proof labels are rechecked by
exact search when importing a claimed optimum. Do not expose full market exports
to locally informed participants.

The pytest suite covers determinism, price validity, concentration, local boundaries,
unique ownership, histories, repeated visits, permanent progress, trade conservation,
messages, budget minimality for a schedule, routing updates, joint feasibility,
hand optima, exhaustive enumeration cross-checks, infeasibility, proof caps,
round trips, fragility and all three demonstrations.

Repository modules separate configuration, models, prices, allocation, tasks,
routing, simulation, scheduling, credits, optimisation, difficulty, serialisation
and validation. Dependencies are NumPy and NetworkX; pytest is the test extra.

## V0.3 final integration validation

`analyse_fragility` now distinguishes `full_affordable_action_fragility` (the
unchanged `decision_fragility`) from `goal_relevant_fragility`. Goal relevance
means the transferred token has a pending requirement somewhere in the pre-action
market; the filter is independent of optimal solutions. Extra unused tokens can
inflate the first fraction while leaving the second zero. Neither measures actual
agent difficulty. `economic_family("goal_relevant_fragile")` demonstrates a bad
ordering of two goal-relevant purchases without decoys. See
[final validation](docs/final_validation.md) for assumptions and reproducible evidence.

For integration, use `validate_economic_state(market, trusted_initial, final, ledger)`
to reconcile balances and provenance against an ordered continuation ledger.
`validate_state` alone checks structure. Keep each transfer `Event` and each
one-credit exploratory `CommunicationEvent(sender, recipient)` in actual order;
execution-message charges are already in transfer events. Reference verification
runs strict reconciliation automatically. The [final report](docs/final_validation.md)
includes a tested import/replay example, trust assumptions and the pilot-readiness verdict.

The [independent protocol review](docs/offer_protocol_review.md) documents corrected
configuration and snapshot-validation defects. Markets now carry explicit protocol
identity checked against configuration and fees. Each reference BUY assumes a
fresh buyer initiation plus the seller's cooperative, free SELL consent; this is
an economic feasibility witness, not a seller-authorisation runtime. The review
also verifies early downstream demand followed by intermediary acquisition.
