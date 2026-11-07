# Revised OFFER / WITHDRAW / BUY protocol

## Model and scope

The graph, ownership allocation, tasks, path candidates, price modifications and
reference transfer order are unchanged. Prices remain directed, finite and positive.
The generator proves that a sequential legal execution exists. It does not prove
that locally informed autonomous agents will discover or choose that execution.
No exploration-environment integration, agent runtime, broker or asynchronous
transaction service is included.

`Offer(id, token, seller, buyer)` costs the buyer exactly one credit immediately.
The prospective seller need not possess the token. No purchase money, token or
capacity is reserved. The standing offer remains active until that buyer withdraws
it, its associated BUY succeeds, or the enclosing episode ends. IDs cannot be
reused within the state. Multiple distinct offers can name the same token,
buyer/seller pair or competing buyers. Token ownership changes do not touch them.

`Withdraw(id, buyer)` closes that buyer's active offer. It costs zero and gives no
refund. `Buy(id, buyer)` checks the matching active offer, seller ownership and
buyer affordability at execution. It atomically moves exactly one token and the
matrix price, with zero additional communication charge. The associated offer
alone becomes fulfilled. A failed BUY leaves the immutable snapshot and active
offer unchanged. Sequential atomic state transitions prevent conflicting buys;
there is no overlapping reservation or escrow to account for in this reference.
Historical task satisfaction persists and completed agents can keep circulating
and reacquiring tokens. Free withdrawals do not change progress or money.

## Accounting

For an OFFER by buyer b: `balance[b] -= 1`.
For BUY from s to b at p=P[b,s]: `balance[b] -= p; balance[s] += p`.
WITHDRAW changes no balances. Standing offers incur no recurring cost.
Thus total credits fall only when offers are issued (and separately accounted
exploratory messages, if a caller uses the older exploration helper). Trade prices
are **gross payments**, not consumed credits.

`protocol_budgets(market, actions)` computes componentwise minimum initial balances
for a fixed ordered explicit plan by maximum prefix deficits. OFFER debits occur
where issued, BUY affordability is checked at settlement, and previous sale receipts
can finance later purchases. This is not a globally minimum endowment. Leeway
retains its existing absolute/relative ceiling rules. The default reference expands
each transfer to exactly one OFFER followed by its BUY, so its budget requirement
is numerically identical to the old default one-message compact step.

## Interfaces and compatibility

- `OfferState(economy=initial_state)` starts with no offers. `offers` retains all
  issued requests and their active/fulfilled/withdrawn status; `ledger` records
  ordered protocol actions. `offer_messages` counts all OFFER costs, including
  later withdrawals. Settlement events in `economy` have zero message fields.
- `apply_protocol` and `replay_protocol` execute immutable deterministic actions.
  `validate_offer_execution(market, trusted_initial, final, ledger)` independently
  reconciles both active offers and economic/provenance state, including every
  intermediate balance. Trusted checkpoints may include already outstanding offers.
- `Solution.actions` remains a transfer projection. Newly generated default
  reference and optimal solutions also export `protocol_actions`, with `kind`
  discriminators OFFER/BUY/WITHDRAW. `decode_protocol` and the result decoder
  reconstruct them. Old exports without this optional field are supported.
- `verify_protocol_solution` checks arbitrary explicit solution plans, including
  withdrawals, against transfers, actual OFFER count, gross payments and complete
  tasks. `verify_solution` retains the compact reference-plan interface and additionally
  verifies its legal explicit normal-form execution; it returns the compatible
  compact State. Use the explicit verifier for plans with extra/withdrawn offers.
- `execute(Transfer)`, `replay`, legacy State event fields and the existing economic
  validator remain the compact reference projection. Under default policy (1,0),
  its buyer-message allocation represents the just-in-time OFFER; it never implies
  a second BUY tax. `OfferState.economy` is a settlement-only snapshot: OFFER fees
  live in the surrounding OfferState and its ledger. Do not validate this projection
  alone using the compact fixed-message validator.
- Nonstandard historical fees require `MarketConfig(communication_protocol=
  'legacy_fixed_messages', ...)`. Those markets are explicitly labelled in metadata;
  old snapshots infer that mode on import. Historical seller-fee examples and
  benchmark reports are retained for reproducibility, not current-game claims.

No local observation fields were broadened. Full market/offer ledgers remain
private generator data; only incident requests should eventually be exposed by
an integrating environment's own messaging interface.

## Exact optimality scope

Start with no existing offers and a full-information feasible sequence. Delete
all unused offers and their withdrawals. Move each remaining OFFER to immediately
before its unique successful BUY. It does not reserve anything or constrain other
transactions; delaying its debit keeps the buyer's intervening balance at least
as high. At its BUY the combined tax plus price is affordable because the postponed
credit has been retained. Ownership and all successful buys stay unchanged.

Therefore a lexicographically optimal solution has a just-in-time normal form:
one OFFER per transaction, no withdrawals. The existing compact exact solver and
its lower bounds remain valid for that scope. It still emits explicit executable
plans and honest cap/proof statuses. There is no solver for arbitrary already-open
OfferStates; do not discard their offer information and interpret a compact search
as proving optimality for that different state. Discovery messages are not optimised.

## Reproduced generated example

Run `python examples/offer_buy_market.py`. With three agents/tokens, task sizes
1–3, relative leeway .2 and seed 42, the verified reference has:

| Quantity | Value |
|---|---|
| OFFER / BUY / WITHDRAW counts | 5 / 5 / 0 |
| Communication expenditure | 5 |
| Gross trading expenditure | 33 |
| Reference budgets | (9,26,0) |
| Initial balances after leeway | (11,32,0) |
| Final balances | (16,6,16) |
| Active offers after completion | 0 |
| Proven optimum objective | (5,5,33) |

Initial total 43 becomes 38: exactly five credits were consumed, while 33 credits
were redistributed through trading. This particular reference equals the proven
optimum; that conclusion is instance-specific, not a property of the scheduler.
The generated result is stored in `examples/markets/offer_buy_market.json` and
includes config, seed, explicit plan, budgets, statuses, difficulty and metadata.

## Validation and modified components

The complete suite passes **118 tests** on Python 3.12.14, retaining the previous
105 cases (the zero-fee solver ablation now explicitly selects historical mode).
Thirteen focused cases cover upfront OFFER charges, free non-refunding WITHDRAW,
untaxed BUY, insufficient settlement money after another OFFER, ownership cycles,
original offers surviving seller loss/reacquisition, multiple standing offers,
completed-agent trading, failed/conflicting buys, correct seller payments,
prefix-minimum budgets with earlier sale financing, configurable leeway,
serialization, strict ledger corruption checks and closed/unknown offer rejection.
The generated example passes JSON Schema and typed result round-trip validation.
The external AnyIO pytest deprecation warning remains non-failing.

The new `offers.py` contains only deterministic sequential state transitions,
fixed-plan budget accounting and independent ledger validation. Scheduling exports
and verifies the explicit plan; credits delegate default accounting to its action
prefixes; generation adds protocol/final-balance metadata; serialization/schema
support the additive action list; the exact solver emits that plan for witnesses.
Configuration explicitly separates historical fee policies. Routing, price
sampling/modification, token allocation and task generation were not changed.

## Independent review clarifications

### Seller consent and buyer autonomy

A BUY in this deterministic witness is shorthand for **a fresh buyer initiation,
the named seller's free consenting SELL, and atomic settlement**. Seller consent
is assumed cooperative for the chosen reference transactions, not established by
the ledger or inferred from an outstanding OFFER. The layer is not a unilateral
purchase runtime. It models neither refusal nor the asynchronous delay between
BUY and SELL. The reference proves conditional economic executability, not that
an autonomous seller would consent. Consent is assumed independent of signalling
history and imposes no extra charge or deadline. Without these assumptions the
normal-form proof does not justify optimality for a different game.

An old OFFER never settles automatically. Only a new `Buy(id, original_buyer)`
can execute it; the seller cannot invoke it in the buyer's name through its own
actor ID. A buyer who acquires the token elsewhere may leave old offers active
or withdraw them for free, without being compelled to buy again.

### Explicit model identity

`Market.communication_protocol` stores `offer_buy` or `legacy_fixed_messages`.
Generation sets it explicitly from the configuration. Protocol and fee equality
are both checked by `prepare_market` and typed result import. Equal fees do not
make a legacy market an OFFER/BUY market. To preserve old constructor and JSON
compatibility only, omitted identity is resolved once at that boundary; it is
then stored explicitly. Changing fees via `replace` does not silently change a
market's declared protocol. Old contradictory exports are rejected rather than
certified under the wrong model.

### Snapshot validation and trust

Explicit verifiers now check state dimensions, provenance, progress, integer
balances/counters and standing-offer IDs/statuses even for an empty ledger.
Settlement snapshots allow zero-message BUY events; compact-prefix events retain
their original message allocation. Their economic reconstruction remains an
independent ledger calculation. These structural checks do not authenticate the
starting endowment or prove its past economic history: the starting checkpoint
and any prior consent remain trusted inputs.

### Early downstream demand example

Let A=0, B=1, C=2, token 0 initially owned by C, and only A require it.
With P[A,B]=3, P[B,C]=2 and initial balances (4,3,0), the explicit plan

```python
plan = (Offer(0, 0, 1, 0),   # A requests T from B, who does not yet own it
        Offer(1, 0, 2, 1),   # B requests it from C
        Buy(1, 1),          # cooperative SELL by C: B acquires T
        Buy(0, 0))          # cooperative SELL by B: A uses its original offer
```

finishes with balances (0,3,2) and history (C,B,A). Two credits are consumed;
prices 2 and 3 are redistributed. The original A-to-B demand remains active
through B's acquisition. This demonstrates representation and verification of
an explicit downstream/upstream signal sequence. It does not establish that
agents discovered it or that normal-form schedules exhibit demand propagation.
See the independent review and executable regression in `test_protocol_review.py`.
