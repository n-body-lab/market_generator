# Engineering review response

Four sequential, tested milestones preserve V0.1 models, enforcement and local
views; no agents or downstream HIVEMARKET integration were introduced.

1. **Controllability**: final-price structural measurements, inclusive constraint
   intervals, bounded rejection, explicit failures with attempt evidence, and
   dependency-targeted price changes. Task depth sampling uses available routing
   depth rather than a hard-coded 0–3. Presets constrain actual indirect fractions;
   ownership concentration remains a sampling knob with optional realised HHI
   constraints. Definitions are in `controllability.md`.
2. **Decision fragility**: exact destructive/affordable fraction, null on unresolved
   actions, separate no-action classification, horizon-limited sequence counts,
   one-credit and alternative-buyer sensitivity, and reference financing dependence.
   Three families prove F=0, 1/2 and 5/6 with an independent deadlock argument.
3. **Optimisation**: profile/ablation before improvement, compact bitmask search,
   admissible consistent bounds, incumbent pruning, optional time limits, bounds
   and lexicographic gaps. Canonical conclusion fields distinguish optimal,
   feasible, infeasible and unknown while keeping legacy termination fields.
   Standard-size markets receive a capped attempt. No heavy dependency was needed.
4. **Characterisation**: 100 seeds per condition in routing, paired budget,
   ownership/overlap and reference-quality studies, plus preset distributions and
   an incompatible-constraint negative control. Raw compressed JSON, distribution
   summaries, human-readable reports and replayable example exports are committed.

The original 48 tests are preserved. Added tests cover constraints against hand
paths, exhaustion, determinism, incompatible requests, measured economic families,
exact deadlocks, pairing, null fragility, time/state limits, bounds against uniform
cost, zero-message search, archived failures/unknowns and example imports.

## Evidence and unresolved questions

See `difficulty_validation.md` and `optimality_benchmarks.md` for measured results.
Depth constraints alter accepted route distributions. In the paired economic
family, one credit of per-agent leeway removes destructive first actions. However,
concentrating ownership did not monotonically raise fragility, and higher route
depth did not make these small instances intractable. Small references can be
strictly suboptimal. Most pilot standard-size instances still lack an optimality
proof under a small cap. These negative/limited results remain visible.

An exhausted sampler is not an infeasibility proof. Retained alternative counts
are capped proxies. Task/ownership conditioning induces selection bias. Exact
fragility can be unavailable, sequence counts require a horizon, and integer
prices/reference-dependent budgets restrict the model. Actual discovery behaviour
requires communication traces; no discovery minimum is claimed. The full market
is private generator knowledge and default execution messages remain proportional
to transactions. No claim about agent collusion or misalignment follows.
