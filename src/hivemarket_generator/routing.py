"""Bounded k-best candidate walks, plus independent token visitation planning."""
import heapq
import networkx as nx
from .models import Market


def trading_graph(prices: tuple[tuple[int, ...], ...]) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(range(len(prices)))
    graph.add_weighted_edges_from((s, b, prices[b][s]) for s in graph for b in graph if s != b)
    return graph


def candidate_routes(prices: tuple[tuple[int, ...], ...], depth: int = 3,
                     alternatives: int = 3) -> dict[tuple[int, int], tuple[tuple[int, ...], ...]]:
    """Layered k-best DP, O(depth*n^3*k log(n*k)); no all-path enumeration.

    Retains k cheapest walks per source/destination across lengths 1..depth.
    Positive prices ensure the cheapest unconstrained walk is simple. Alternative
    walks may revisit vertices; counts are retained candidates, not all routes.
    """
    if depth < 1 or alternatives < 1:
        raise ValueError('depth and alternatives must be positive')
    graph = trading_graph(prices)
    result = {}
    for source in graph:
        layer = {source: [(0, (source,))]}
        collected: dict[int, list[tuple[int, tuple[int, ...]]]] = {i: [] for i in graph}
        for _ in range(depth):
            next_layer: dict[int, list[tuple[int, tuple[int, ...]]]] = {i: [] for i in graph}
            for node, paths in layer.items():
                for dest in graph.successors(node):
                    next_layer[dest].extend((cost + prices[dest][node], path + (dest,)) for cost, path in paths)
            layer = {node: sorted(paths)[:alternatives] for node, paths in next_layer.items()}
            for node, paths in layer.items():
                collected[node].extend(paths)
        for dest in graph:
            if dest != source:
                result[source, dest] = tuple(path for _, path in sorted(collected[dest])[:alternatives])
    return result


def independent_token_route(market: Market, token: int, exact_demand_limit: int = 8) -> tuple[int, ...]:
    """Minimise gross cost ignoring credits for <=8 demanders, else nearest demand.

    Product-state Dijkstra permits repeat visits, and has no candidate depth cap.
    This single-token objective deliberately differs from joint lexicographic cost.
    """
    source = market.initial_owners[token]
    required = frozenset(i for i, task in enumerate(market.tasks) if token in task) - {source}
    if len(required) > exact_demand_limit:
        graph = trading_graph(market.prices)
        route = (source,)
        while required:
            paths = nx.single_source_dijkstra_path(graph, route[-1])
            dest = min(required, key=lambda d: (sum(market.prices[b][a] for a, b in zip(paths[d], paths[d][1:])), d))
            route += tuple(paths[dest][1:])
            required -= set(route)
        return route
    start = (source, required)
    queue = [(0, (source,), start)]
    best = {start: 0}
    while queue:
        cost, path, key = heapq.heappop(queue)
        node, remaining = key
        if cost != best[key]:
            continue
        if not remaining:
            return path
        for dest in range(market.n_agents):
            if dest == node:
                continue
            next_key = (dest, remaining - {dest})
            next_cost = cost + market.prices[dest][node]
            if next_cost < best.get(next_key, float('inf')):
                best[next_key] = next_cost
                heapq.heappush(queue, (next_cost, path + (dest,), next_key))
    raise RuntimeError('complete price graph must admit a route')
