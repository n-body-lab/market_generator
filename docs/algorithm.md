# Generation pipeline

1. Validate config; initialise `numpy.random.default_rng(seed)`. Repeat steps 2–10 for at most
   `generation_attempt_limit` candidates, testing realised structural constraints
   under final prices. Exhaustion raises `GenerationFailure`; it is not a proof
   that the requested combination is mathematically impossible.
2. Draw integer P; optionally symmetrise; set unused diagonal to zero.
3. Allocate token IDs via Dirichlet weights and categorical owner draws.
4. Build a NetworkX ownership-direction graph with weight P[next,current]. Compute
   bounded k-best candidate walks by layered dynamic programming, retaining k
   labels per destination at each layer. This avoids enumerating all walks.
5. Sample an integer task size uniformly in the configured inclusive range per
   agent. Sample a target hop count from zero to the largest cheapest retained path depth, then sample tokens without
   replacement with weight 1/(1+|candidate_hops-target|). Initially held tokens have
   hop count zero. Counts and overlapping requirements vary independently.
   This explicit route bias is a minimal V0.1 choice, not an agent model.
6. For each requested modification choose an actual initially unmet owner-to-demander
   dependency (random pair only when none exist), choose a distinct middle, and raise
   P[buyer,seller] above P[middle,seller]+P[buyer,middle]. Later modifications can
   change that opportunity; no claim about a permanent planted shortest path is
   made. Recompute all candidates and token routes under final prices.
7. For each token, run Dijkstra over (current owner, unvisited demanders), minimising
   gross payments. At >8 demanders use full-graph shortest paths to the nearest
   remaining demander, removing every requirement visited along the way.
   The exact-per-token objective ignores budgets and messages. Routes may repeat
   vertices; maximum candidate depth does not restrict whole journeys.
8. Interleave routes in deterministic round-robin token order. Each token's own
   edges remain ordered; only one current owner can sell it.
9. Expand each default reference transfer into one one-credit OFFER and one
   untaxed atomic BUY, then accumulate each agent's net expenditure prefix. Take the maximum prefix plus
   next action's pre-transfer affordability requirement (including the OFFER debit at issue time (seller messages apply only to historical fee models)).
   Allocate that minimum fixed-schedule budget, then add nonnegative leeway.
10. Replay all actions and independently audit payments, affordability, ownership,
    persistent progress and lexicographic costs. A failure raises; it never emits
    a supposedly feasible result. With the generated budgets and complete positive
    graph this constructive schedule is feasible without regeneration.
11. If enabled and dimensions fit, run exact search using the reference incumbent.
    The immutable state key omits histories because future costs in V0.1 depend
    only on ownership, progress and balances. Publish proof status separately from
    the verified incumbent; capped search is never labelled optimal.
12. Compute transparent metrics and export config, seed, assumptions and results.

`prepare_market` starts at step 6's final-price boundary with a supplied market;
its config controls routing candidates, budgets, constraints and optimisation, not price/task
regeneration. All benchmark solutions remain private to the generator.

## Complexity and practical limits

Candidate routing is O(depth*n^3*k*log(n*k)) with bounded retained alternatives,
not an enumeration of all alternative routes. Token-state planning is exponential
in demanders (capped at eight for exact routing). Joint exact search has up to
n^tokens ownership assignments, 2^(total requirements) progress masks and at most
(S+1)^n integer balance vectors for initial credit sum S; reachable combinations
are usually far fewer. The explicit state cap is essential. Metrics that remove
transactions are quadratic in schedule length and describe no replanned optimum.
