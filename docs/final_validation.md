# V0.3 final validation

## Goal-relevant fragility

`analyse_fragility` preserves `decision_fragility` and adds the explicit alias
`full_affordable_action_fragility`: economic fragility over **all** affordable
transfers. Counts of irrelevant actions affect that denominator.

`goal_relevant_fragility` is computed separately over affordable transfers whose
token has at least one **unmet agent-token requirement in the pre-action state**.
Relevance uses neither optimal-solution membership nor the action's feasibility
classification. It includes intermediary forwarding, even if the buyer has no
requirement. Counts, per-action relevance, unknown classifications and bounds are
exported for each subset. No relevant affordable actions means null, not zero;
any unclassified relevant action also makes the relevant fraction null. An
unclassified irrelevant action does not invalidate an exactly classified subset.

This is a transparent full-information filter, not a model of an agent's beliefs.
It can include unhelpful buyers of relevant tokens and exclude useful sales of
unneeded tokens that finance other purchases. Adding irrelevant buyers can still
change its denominator. Neither fraction proves subjective decision difficulty.

### Reproduced experiments

Run `python experiments/fragility_validation.py`. Raw results and a short summary
are in `experiments/data/fragility_v03.json` and `.md`.

| Irrelevant decoys | Full affordable-action fragility | Goal-relevant fragility |
|---:|---:|---:|
| 1 | .500000 | 0 |
| 3 | .750000 | 0 |
| 5 | .833333 | 0 |
| 10 | .909091 | 0 |
| 20 | .952381 | 0 |

The original robust, fragile and highly constrained families remain available.
Their earlier reported fragility is a full-action-space measurement; increasing
unused tokens is not evidence of harder goal-relevant coordination.

`economic_family('goal_relevant_fragile', seed=42)` adds a non-decoy example.
Two agents own one token each and each requires the other's token. Prices are
p=2 at seed 42; buyer and seller each pay one execution-message credit. Initial
balances are (3,4). Both immediate purchases satisfy a pending requirement:

- Agent 1 buys token 0 first: balances become (4,1). Agent 0 can then buy token 1,
  reaching (1,2), completing both tasks.
- Agent 0 buys token 1 first: balances become (0,5). It owns both tokens and cannot
  pay the seller's message fee. There are no affordable transfers; agent 1's task
  can never complete.

Both fractions are exactly 1/2. Seeds 0–4 vary p while retaining this independent
deadlock argument and a proven optimal reference schedule. A replayable export
is `examples/markets/goal_relevant_fragile.json`.

### Tests for the first fix

The complete suite passed **87 tests**, preserving the original 75. Added tests
cover the five decoy counts, hand-verified balances/deadlock over five seeds,
multiple unsatisfied agents, relevance of forwarding, completed requirements,
empty relevant subsets and subset-specific unknown handling. Strict economic
reconciliation and final integration regression results accompany the second fix.

## Strict economic reconciliation

`validate_economic_state(market, trusted_initial, final, ledger)` independently
reconstructs every balance, owner, history, progress set and message counter. It
does not call the simulator's execution/replay implementation. Intermediate
pre-transfer affordability is checked, including seller messages **before** sale
receipts. Trade payments conserve credits; execution and exploratory message
fees consume them. Exact final per-agent balances must match reconstructed books.
It also matches the supplied final transfer-event sequence, including any trusted
prefix. Strict validation accepts incomplete runtime states as well as solutions.

The existing `validate_state` and `decode_state` remain structural checks. A state
snapshot alone cannot authenticate an endowment or reconstruct exploratory-message
senders/order: provide a trusted initial/checkpoint state and all subsequent
ledger records. `State.events` deliberately remains the transfer-only provenance
log. Callers interleave its new `Event` records with `CommunicationEvent(sender,
recipient)` records for one-credit exploratory messages. Execution messages are
already included in transfer events and must not be double-recorded. The ordered
ledger covers only the continuation after the trusted checkpoint; transfer
sequence numbers continue the checkpoint's transfer count. Record actual message
order in the integrating environment. `decode_ledger(loads(dumps(ledger)))` can
round-trip the typed records without asserting their authenticity.

`verify_solution` now runs strict reconciliation on reference and solver witness
replays. Therefore generated solutions and typed result imports receive the
stronger check without changing their public signatures or market format.

### Tests and final regression

The complete suite passes **105 tests**, preserving all previous 75. The 15
ledger cases cover valid multi-token repeat visits, mixed exploratory/transfer
ordering, artificial credit injection, wrong prices and seller payments,
incorrect buyer/seller message charges, unexplained destruction, negative
intermediate balances hidden by later receipts, seller prepayment, omitted and
duplicated message records, altered ownership histories/counters and continuation
anchors. Three additional interface cases check easy/medium/hard reproducibility,
measured constraints, reference feasibility, canonical/legacy optimality status,
complete JSON payloads and exact allowed local-observation fields.

Relevant small experiments were reproduced; the expensive 100-seed benchmark
suites were not rerun. Easy/medium/hard generation and all seven research exports
pass typed import, JSON Schema validation and strict economic replay. Regenerated
legacy economic exports retain their original full-space values and now include
the complementary relevant-subset measurements. Python 3.12.14 was exercised;
the declared Python 3.11 compatibility was not tested on another interpreter.
Pytest's existing external AnyIO deprecation warning remains non-failing.

## Import and use for a controlled pilot

From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
```

```python
from hivemarket_generator import (
    economic_family, CommunicationEvent, validate_economic_state,
    dumps, loads, decode_result, decode_ledger, local_view,
)
from hivemarket_generator.simulation import execute, send_exploratory_message

result = economic_family('goal_relevant_fragile', seed=42)
restored = decode_result(loads(dumps(result)))
market, anchor = restored.market, restored.initial_state
state = execute(market, anchor, restored.reference_solution.actions[0])
ledger = [state.events[-1]]
state = send_exploratory_message(market, state, 0, 1)
ledger.append(CommunicationEvent(0, 1))
state = execute(market, state, restored.reference_solution.actions[1])
ledger.append(state.events[-1])
validate_economic_state(market, anchor, state, ledger)
assert state.balances == (0, 2)
validate_economic_state(market, anchor, state, decode_ledger(loads(dumps(ledger))))
agent_payload = local_view(market, anchor, agent=0)
```

A regular `generate_market(MarketConfig(...))` result exports the full config,
seed/metadata, owner array, tasks, prices, initial balances/progress, reference
solution, honest optimisation status and difficulty measurements. Full exports
and ledgers are generator-side data; give agents only their local views. Do not
expose other inventories/tasks, the global matrix or benchmark schedules.

## Limitations and integration-readiness verdict

Ready for a **controlled integration pilot**, with both targeted fixes validated.
No integration with the main repository is implemented. Ledger validation is a
consistency proof relative to trusted starting balances and the supplied ordered
records, not event authentication, signature verification or evidence of real
external payments. Missing exploratory messages cannot be inferred from token
provenance alone; callers must retain those records. Untrusted snapshots must not
be accepted solely because structural validation passes.

Goal relevance remains a full-information token-demand filter, not a model of
local observations, communication or subjective plausibility. The two fragilities
must be reported with their denominators/statuses. Existing integer-credit,
fixed-message and capped-optimisation limitations remain; feasibility witnesses
are not automatically globally optimal. No optimisation or market-mechanism
expansion was needed.
