# Replayable research examples

Regenerate all six exports with `python examples/research_markets.py` from the
repository root. Load any file with `decode_result(loads(path.read_text()))`.

`easy.json`, `medium.json`, `hard.json` are the robust, fragile and highly
constrained economic families at seed 42. Their exact first-action fragility is
0, 1/2 and 5/6 respectively, stored under `difficulty.decision_analysis`.
These labels describe this toy economic comparison; all three have direct
cheapest requirement paths and proven optimal benchmark schedules.

`structural_easy.json`, `structural_medium.json`, `structural_hard.json` separately
use the constrained six-agent/twelve-token presets. Their realised indirect
fractions at seed 42 are 0, 3/14 and 13/14. These exports disable exact optimisation
and explicitly report feasible/unproven. They demonstrate routing control, not
proven strategic hardness. Full exports contain private generator information.

V0.3 adds `goal_relevant_fragile.json`: both agents have unmet tasks, both affordable
purchases are goal-relevant, and the wrong ordering prevents the other agent from
paying its execution message fee. Full and goal-relevant fragility both equal 1/2.
Regenerate it with `python experiments/fragility_validation.py`. The older three
economic examples remain valid full-action-space measurements; the high-decoy
example has zero fragility in its goal-relevant subset.
