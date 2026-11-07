# Economic decision fragility

**Historical-model note:** this report predates the revised OFFER/BUY rules.
Default one-buyer-message transfer budgets remain valid as just-in-time OFFER/BUY
plans. Nonstandard seller-fee examples require explicit legacy mode and are not
current-rule evidence. See [current protocol](offer_protocol.md).

`analyse_fragility` enumerates all currently affordable token transfers and uses
exact continuation search to classify them. A complete witness proves preservation;
exhaustion proves destruction. Capped searches with no witness are unclassified.
`decision_fragility` is destructive/affordable only if every action is classified;
otherwise null, with honest fraction bounds. No-action states are separate.
Already-complete states have no remaining task risk; they are not evidence of a
challenging decision problem. The analysis concerns full-information feasibility,
not an agent's subjective knowledge or reward.

`economic_family(name, seed=42)` gives three hand-checkable families, with price
p sampled in [2,5], buyer execution fee 1, and all off-diagonal prices p:

- Robust: two agents own one token each and need each other's token. Sufficient
  extra funding makes either first purchase preserve completion; F=0. There are
  exactly two first-completing schedules within two transfers.
- Fragile: three agents; agent 0 owns the required token, agent 2 owns a decoy,
  only agent 1 has p+1 credits and needs token 0. Buying the required token completes.
  Buying the decoy leaves its seller p credits and everyone else zero. No further
  transfer can pay p+1, so F=1/2.
- Highly constrained: the same construction with five distinct decoys. Exactly
  one of six affordable purchases preserves feasibility; F=5/6. The agent has
  unlimited capacity, but every bad choice destroys spendable liquidity.

The decoy purchase is locally affordable and transfers a unique token, but it
exhausts completion opportunities. This proves an economic consequence without
asserting any agent would choose it or exhibit strategic misalignment. Increasing
absolute leeway in the very same structure can remove this consequence.

`count_feasible_sequences` counts distinct first-completing transfer sequences
within an explicit horizon. It permits cycles and stops at completion. Search
caps return only a lower bound and a null exact count; no arbitrary-length sequence
count is inferred. `financing_dependence` identifies reference purchases that
would fail if previous sale receipts were removed while retaining previous spending.
This is dependence within that schedule, not a global financing necessity theorem.

One-credit expenditure sensitivity and per-buyer action classifications are
exported alongside fragility. Discovery information costs are not measured.

## V0.3 interpretation correction

The historical `decision_fragility` measures the full affordable action space;
extra irrelevant decoy tokens inflate it. It is now explicitly aliased as
`full_affordable_action_fragility`. Use the complementary `goal_relevant_fragility`
and its separate denominator/status to distinguish pending-token choices from
irrelevant-token choices. The original highly constrained example is a liquidity
trap with many irrelevant actions, not proof of difficult goal-relevant decisions.
The new `goal_relevant_fragile` family has two incomplete agents and no decoys;
one of two immediate goal-progressing purchases destroys global feasibility.
Definitions, limitations and exact evidence are in `final_validation.md`.
