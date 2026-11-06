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
