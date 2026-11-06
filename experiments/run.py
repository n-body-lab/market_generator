"""Run A/B/C: python experiments/run.py --seeds 0 1 2 --output experiments/results/demo.json."""
import argparse
from dataclasses import replace
from itertools import permutations
from pathlib import Path
import numpy as np
from hivemarket_generator import Market, MarketConfig, prepare_market, dumps
from hivemarket_generator.simulation import replay
from hivemarket_generator.models import complete


def routing_experiment(seeds: list[int]) -> list[dict]:
    rows = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        order = [int(x) for x in rng.permutation(4)]
        prices = [[0 if i == j else 50 for j in range(4)] for i in range(4)]
        for a, b in zip(order, order[1:]):
            prices[b][a] = int(rng.integers(1, 4))
        for span in (1, 2, 3):
            tasks = [frozenset() for _ in range(4)]
            tasks[order[span]] = frozenset({0, 1})
            tasks[order[1]] |= {1}  # mixed/shared demands
            market = Market(tuple(tuple(row) for row in prices), tuple(tasks), (order[0], order[0]))
            config = MarketConfig(n_agents=4, n_tokens=2, task_dependency_range=(0, 2), seed=seed)
            r = prepare_market(market, config)
            rows.append({'seed': seed, 'controlled_chain_span': span, 'routing': r.difficulty['routing'],
                         'reference_objective': r.reference_solution.objective})
    return rows


def resource_experiment(seeds: list[int]) -> list[dict]:
    rows = []
    for seed in seeds:
        price = int(np.random.default_rng(seed).integers(2, 6))
        market = Market(((0, price), (price, 0)), (frozenset({1}), frozenset({0})), (0, 1))
        for slack in (0, 1, price + 1):
            config = MarketConfig(n_agents=2, n_tokens=2, task_dependency_range=(1, 1), seed=seed,
                                  budget_leeway=slack, leeway_mode='absolute')
            r = prepare_market(market, config)
            feasible = 0
            orders = list(permutations(r.reference_solution.actions))
            for actions in orders:
                try:
                    feasible += complete(market, replay(market, r.initial_state, actions))
                except ValueError:
                    pass
            rows.append({'seed': seed, 'price': price, 'absolute_leeway': slack,
                         'budgets': r.initial_state.balances, 'sequences_tested': len(orders),
                         'feasible_sequences': feasible, 'optimality_status': r.optimality_status})
    return rows


def joint_experiment(seeds: list[int]) -> list[dict]:
    rows = []
    for seed in seeds:
        direct = int(np.random.default_rng(seed).integers(6, 10))
        market = Market(((0, 1, 9), (1, 0, 1), (direct, 1, 0)),
                        (frozenset(), frozenset(), frozenset({0, 1})), (0, 0))
        config = MarketConfig(n_agents=3, n_tokens=2, task_dependency_range=(0, 2), seed=seed,
                              budget_leeway=30, leeway_mode='absolute')
        r = prepare_market(market, config)
        rows.append({'seed': seed, 'independent_reference': r.reference_solution.objective,
                     'best_joint': r.best_solution.objective,
                     'optimality_status': r.optimality_status,
                     'proof': r.metadata.get('exact_search')})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', nargs='+', type=int, default=[0, 1, 2])
    parser.add_argument('--output', type=Path, default=Path('experiments/results/demo.json'))
    args = parser.parse_args()
    data = {'assumptions': 'Controlled constructed families; messages=transactions; not discovery communication.',
            'A': routing_experiment(args.seeds), 'B': resource_experiment(args.seeds),
            'C': joint_experiment(args.seeds)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dumps(data))
    print(f'Wrote {args.output}; {len(data["A"])} routing, {len(data["B"])} resource, {len(data["C"])} joint cases')


if __name__ == '__main__':
    main()
