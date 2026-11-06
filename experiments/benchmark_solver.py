"""Reproducible A*/uniform-cost ablation; baseline historical runs retained separately."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from hivemarket_generator import MarketConfig, generate_market, solve_exact
from hivemarket_generator.optimization import reference_quality


def run(seeds: int = 5, state_limit: int = 5000) -> list[dict]:
    rows = []
    for n, k in [(2, 2), (3, 2), (3, 3), (4, 3), (4, 4), (6, 12)]:
        for seed in range(seeds):
            config = MarketConfig(n_agents=n, n_tokens=k, task_dependency_range=(1, min(k, 3)),
                                  exact_state_limit=0, seed=seed)
            r = generate_market(config)
            for bound in (False, True):
                start = perf_counter()
                out = solve_exact(r.market, r.initial_state, state_limit, r.reference_solution,
                                  use_lower_bound=bound)
                rows.append(dict(n_agents=n, n_tokens=k, seed=seed, state_limit=state_limit,
                                 use_lower_bound=bound, seconds=perf_counter()-start,
                                 status=out.conclusion, termination=out.termination_reason,
                                 expanded=out.expanded_states, discovered=out.discovered_states,
                                 incumbent=out.best_solution.objective, lower_bound=out.lower_bound,
                                 gap=out.optimality_gap,
                                 quality=reference_quality(r.reference_solution,
                                                           out.best_solution if out.status == 'optimal' else None)))
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=5)
    parser.add_argument('--state-limit', type=int, default=5000)
    parser.add_argument('--output', type=Path, default=Path('experiments/data/solver_improved.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(run(args.seeds, args.state_limit), indent=2)+'\n')
    print(args.output)
