"""Full-information structural constraints; no claim about necessary agent routes.

An indirect dependency means the least-payment source-to-demander path uses >1
edge (minimise hops among price ties). Direct trades always remain possible.
Fractions use unmet initial requirements; empty denominators yield zero.
"""
from collections import Counter
from typing import TYPE_CHECKING
import networkx as nx
from .routing import trading_graph
if TYPE_CHECKING:
    from .config import MarketConfig
    from .generation import GenerationResult

PROPERTY_NAMES = {'indirect_dependency_fraction', 'mean_dependency_depth', 'shared_demand_fraction',
                  'ownership_hhi', 'shared_intermediaries', 'limited_slack_fraction',
                  'competitive_alternative_fraction'} | {f'depth_{i}_fraction' for i in range(1, 33)}


def requested_properties(config: 'MarketConfig') -> dict[str, tuple[float, float]]:
    requested = dict(config.structural_constraints or {})
    if config.target_indirect_dependency_fraction is not None:
        lo, hi = requested.get('indirect_dependency_fraction', (0, 1))
        requested['indirect_dependency_fraction'] = (max(lo, config.target_indirect_dependency_fraction), hi)
    return requested


def realised_properties(result: 'GenerationResult') -> dict[str, float]:
    m = result.market
    graph = trading_graph(m.prices)
    # Integral cost tie-break: a simple minimum path uses at most n-1 hops.
    paths = dict(nx.all_pairs_dijkstra_path(graph, weight=lambda a, b, data: data['weight'] * (m.n_agents + 1) + 1))
    dependencies = [(m.initial_owners[t], i) for i, task in enumerate(m.tasks)
                    for t in sorted(task) if m.initial_owners[t] != i]
    depths = [len(paths[a][b])-1 for a, b in dependencies]
    count = len(depths)
    demand = Counter(t for task in m.tasks for t in task)
    intermediaries = Counter(i for a, b in dependencies for i in paths[a][b][1:-1])
    alternatives = 0
    for a, b in dependencies:
        retained = [p for p in result.candidates[a, b] if len(p) == len(set(p))]
        costs = sorted(sum(m.prices[y][x] for x, y in zip(p, p[1:])) for p in retained)
        alternatives += len(costs) > 1 and costs[1] <= 1.25 * costs[0]
    values = {
        'indirect_dependency_fraction': sum(d > 1 for d in depths) / count if count else 0,
        'mean_dependency_depth': sum(depths) / count if count else 0,
        'shared_demand_fraction': sum(v for v in demand.values() if v > 1) / sum(demand.values()) if demand else 0,
        'ownership_hhi': sum((m.initial_owners.count(i) / m.n_tokens)**2 for i in range(m.n_agents)) if m.n_tokens else 0,
        'shared_intermediaries': sum(v > 1 for v in intermediaries.values()),
        'limited_slack_fraction': sum(((b-r)/r <= .1 if r else b == 0)
                                      for b,r in zip(result.initial_state.balances,result.reference_budgets)) / m.n_agents,
        'competitive_alternative_fraction': alternatives / count if count else 0,
    }
    values.update({f'depth_{d}_fraction': depths.count(d) / count if count else 0 for d in range(1, 33)})
    return values


def satisfies(requested: dict, realised: dict) -> bool:
    return all(lo <= realised[name] <= hi for name, (lo, hi) in requested.items())
