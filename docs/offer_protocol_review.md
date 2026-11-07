# Independent engineering assessment of OFFER/BUY branch

## Pre-correction assessment (reviewed commit 7d9b0da)

**Verdict: not ready to merge before two P1 corrections.** No P0 defect was found
in the generated default reference accounting or the compact exact-search proof.
The original suite was executed independently: 118 passed on Python 3.12.14.
The external AnyIO deprecation warning is unrelated and non-failing.

### Confirmed findings

1. **P1 — conflicting economic models accepted.** `generation.prepare_market` and
   `offers.uses_offer_protocol` select the model from fees, without reconciling
   supplied configuration. Reproducer: construct a two-agent, one-token Market
   with `ExecutionMessages(0,0)`; call `prepare_market` with default OFFER/BUY
   config, dimensions 2/1 and task range (0,1). It accepts and reports config
   `offer_buy`, metadata `legacy_fixed_messages`, and a zero-message transfer.
   Consequence: an exported requested model differs from the executed economics.
   Minimum correction: an explicit market protocol field, compatibility inference
   only at old construction/import boundaries, and protocol AND fee agreement at
   prepare/import boundaries. Equal legacy/default fee numbers must not choose
   the protocol implicitly.
2. **P1 — invented task progress accepted by explicit verifier.**
   `scheduling.verify_protocol_solution` and `offers.validate_offer_execution` do
   not check provenance/progress consistency at their snapshot boundary. Start
   with token 0 owned only by agent 0 and agent 1 requiring it. Replace progress
   with `(empty,{0})` while history stays `(0,)`. Verifying `Solution((),(0,0,0),())`
   accepts it as complete. Consequence: a public verifier can certify an impossible
   solution if a caller supplies a corrupted checkpoint. Minimum correction:
   structural validation of compact inputs and explicit settlement snapshots,
   while keeping trusted starting BALANCES as a separate authentication assumption.
3. **P2 — empty replay skips mode validation.** `offers.replay_protocol` returns a
   legacy snapshot unchanged for an empty action tuple although a nonempty tuple
   rejects that market. Minimum correction: validate mode and initial snapshot
   before iteration, including empty schedules.

4. **P2 — per-agent leeway shape accepted then rejected during generation.**
   `config.MarketConfig` accepts `(0.2,)` for two agents, but `credits.add_leeway`
   rejects it later. Scalars broadcast; tuples are documented per-agent vectors.
   Minimum correction: validate tuple length against agent count when constructing
   the config. No budget formula change is required. This was reproduced while
   checking liquidity inputs after the initial assessment.

### Acceptable abstractions and potential risks (not confirmed economics bugs)

- Seller consent is absent as a separate action. This is acceptable ONLY if a BUY
  ledger entry means a freshly buyer-initiated purchase plus the seller's assumed
  free SELL consent and atomic settlement. It is not a general unilateral-buy
  runtime, nor evidence a seller would accept. Document this conditional witness;
  do not add asynchronous broker infrastructure.
- Persistent non-owner demand is representable, but a just-in-time reference does
  not demonstrate decentralised discovery. Add an early downstream offer / later
  upstream acquisition example, without changing the optimiser.
- Compact `verify_solution` has a narrower contract than arbitrary protocol plans;
  the latter use `verify_protocol_solution`. Keep the distinction explicit.
- Trusted initial balances/events are anchors, not authenticated facts. The
  independent validator shares ID checks with execution; counterexamples therefore
  need hand arithmetic and malformed snapshot tests, not only self-replay checks.

### Mathematical assessment before correction

For a FIXED plan each agent's minimum endowment is its largest prefix funding
requirement, including an OFFER debit when issued and purchase price at BUY.
Earlier sales reduce net expenditure. Taking componentwise maxima is necessary
and sufficient because all payments and their ordering are fixed. This is not a
global minimum budget allocation.

For empty initial offers, static prices, nonbinding signals, no deadlines or
additional consent/message charges, and cooperative/history-independent seller
consent, unused offers/withdrawals may be removed. Each used OFFER may be delayed
to just before its BUY, weakly increasing earlier balances and retaining the one
credit needed for the delayed tax. Ownership, transfers, progress and gross cost
are unchanged. Thus a full-information optimal normal form exists and the compact
solver/lower bounds remain valid. This proof does not hold as stated for sunk
prepaid outstanding offers, discovery-dependent decisions or costly/refused SELLs.
State/label/time caps still distinguish proof from a verified incumbent.

### Smallest required correction set

Fix protocol/config/import agreement and snapshot validation; cover empty inputs.
Add deterministic demand-propagation, obsolete-offer autonomy, checkpoint, budget
exhaustion and pending-offer scope cases. Document assumed seller consent. Preserve
graph generation, routes, search algorithm, dependencies and the existing branch.

## Post-correction evidence

### Corrections

- `Market.communication_protocol` is stored explicitly; only missing historical
  identity is inferred at construction/import. Dispatch now reads that field.
  `validate_market_config` rejects mismatched protocols, fee counts or dimensions
  before preparation/import can certify a result. Same-fee legacy markets remain
  legacy. Solver proof-scope metadata also follows that declared identity, not
  fee equality. Old omitted fields are supported; inconsistent data are not.
- Compact initial states undergo structural validation before explicit solution
  verification. `validate_offer_execution`, replay and direct protocol application
  also check snapshot shape, ownership/provenance/progress, retained offer IDs and
  statuses, and offer counters. The generic structural validator has a narrowly
  used settlement-event option; default compact validation is not weakened.
- Per-agent leeway vectors now fail at configuration time if their length differs
  from the number of agents; scalar leeway broadcasting is unchanged.
- Empty replay validates the selected model and snapshot. Passing OfferState to
  the compact solver now gives an explicit unsupported-scope error rather than
  an attribute error. The solver algorithm/bounds were not changed.
- Metadata and documentation disclose assumed free seller SELL consent. Fresh
  buyer initiation is still required; outstanding demand cannot compel purchase.
  No asynchronous broker or speculative permission mechanism was added.

### Post-correction adversarial and mathematical evidence

The new `tests/test_protocol_review.py` covers the two confirmed P1 counterexamples,
empty legacy execution, explicit same-fee legacy identity, inconsistent fees,
conflicting serialized declarations, historical import compatibility, five forms
of malformed checkpoint, invalid offer statuses/IDs/counters, early downstream
requests, and acquisition elsewhere without forced fulfilment of old demand.

For three asymmetric integer price scales and four fixed plans (single sale,
early offer with later financing, withdrawn unused demand, and token revisits),
every initial balance pair in a finite grid is enumerated. Executability agrees
exactly with the componentwise prefix-minimum budget orthant. Existing tests
independently cross-check exact search against enumeration/uniform-cost search,
and cover caps, zero-fee legacy cases, credit conservation and provenance cycles.

A pending prepaid offer is an explicit counterexample to extending the empty-offer
normal-form theorem blindly: with price 2, a buyer with 2 credits after paying its
OFFER can BUY, while a fresh OFFER+BUY at the same projected balances is infeasible.
The compact solver intentionally solves the latter problem; its API rejects the
full pending OfferState. Dropping offer information before calling it changes the
problem and cannot establish a proof for the original state.

The independent ledger verifier reconstructs transactions, money and status without
calling execution/replay. It shares basic ID validation and snapshot structural
checks with execution, so this is implementation diversity, not a formally verified
second engine. Hand arithmetic, malformed-checkpoint counterexamples and exhaustive
endowments supplement replay comparisons. Trusted anchors, authentication and
seller behaviour remain outside the proof.

### Final verdict

**Ready to merge as a standalone, cooperative reference generator after these
corrections.** No P0 defect was confirmed; both P1 defects and the small P2 boundary
issues are corrected with regressions. Reference feasibility and fixed-plan budget
minimality are valid under the documented static, sequential economics. Optimality
is conditional on the full-information empty-offer/cooperative-consent model and
only claimed when exact search establishes it. Explicit demand propagation is
representable and verified; autonomous discovery/coordination is not demonstrated.

Final complete-suite counts and export validation are recorded below.

### Executed final checks

- Baseline: **118 passed** before implementation changes.
- Corrected branch: **135 passed**, including 17 new review regression cases.
  Existing exact-field and fee-replacement tests were minimally updated for the
  explicit protocol field; their economic assertions remain intact.
- All eight committed example exports passed JSON Schema and typed import. All
  current-protocol examples also passed explicit protocol replay. Historical
  seller-fee examples remain labelled legacy and cannot be presented as current.
- The regenerated seeded 3-agent/3-token reference still uses five offers, five
  buys, 33 gross payments, initial balances (11,32,0), final balances (16,6,16),
  and proven optimum (5,5,33). Routing/allocation/search algorithms were unchanged.
- `git diff --check` passed. No new dependencies, agents, broker runtime,
  asynchronous escrow or exploration-repository changes were introduced.

Residual limitations: consent, endowments and past checkpoint economics are trusted;
structural consistency is not cryptographic authentication. The fee/protocol schema
field remains optional only for historical imports. The independent verifier
shares structural/ID checks with execution. Explicit signals are verified, but no
claim about their discovery cost, subjective plausibility or emergent coordination
is supported. Optimality from a pending-offer state is still outside the compact
solver contract. No unresolved P0/P1 issue remains within this stated scope.
