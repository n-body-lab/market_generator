# Constraint-aware generation

`target_indirect_dependency_fraction=0.5` requests **at least** half the initially
unmet requirements have a cheapest-payment path of two or more edges. This is an
economic routing property, not a claim direct trades are impossible. Price ties
prefer fewer hops. Measurements use unrestricted paths under final prices; the
candidate depth limits only retained alternatives and task sampling bias.

`structural_constraints` maps property names to inclusive `(lower, upper)` ranges:

- `indirect_dependency_fraction`, `mean_dependency_depth`, `depth_1_fraction`, ...,
  `depth_32_fraction`: cheapest-path hop distribution over unmet requirements.
- `shared_demand_fraction`: fraction of all requirements on tokens demanded by
  at least two agents, including initially met requirements.
- `ownership_hhi`: sum of squared initial ownership shares.
- `shared_intermediaries`: agents interior to cheapest paths for two or more
  requirements (counts occurrences, not indispensable vertices).
- `limited_slack_fraction`: resource metric using relative slack <=0.1, with zero
  reference and zero absolute slack classified limited.
- `competitive_alternative_fraction`: unmet requirements with two retained simple
  candidate paths whose costs differ by at most 25%. This is a capped proxy.

Empty denominators yield zero. Ownership's Dirichlet concentration remains a
sampling parameter; HHI constraints bound the actual draw. Fraction intervals
can intentionally be impossible: bounded rejection produces an explicit failure.
No scalar difficulty score is defined.

`generation_attempt_limit` defaults to 100. A seeded RNG stream creates candidates;
prices are modified at actual owner-to-demander dependencies. All paths and
measurements are recomputed under the modified prices. Candidate screening skips
exact joint optimisation. Accepted structures are benchmarked with the original
config. A `GenerationFailure` includes attempts, requested intervals and last
measurements; exhaustion proves only failure to sample, not mathematical
nonexistence. `prepare_market` checks supplied structures once and fails if they
violate constraints. Generation metadata records requested/realised properties,
constraint satisfaction and attempt count; no nondeterministic timing enters the
market export.

Presets now constrain disjoint indirect-fraction ranges: easy [0,.15], medium
[.2,.5], hard [.6,1]. This is explicit conditional sampling, not evidence of
strategic difficulty. Overrides may make constraints impossible. Rejection
conditions alter the distribution and can bias ownership/overlap as well.
