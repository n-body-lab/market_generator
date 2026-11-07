"""Exact A*/branch-and-bound over integral economic states, with honest limits."""
from dataclasses import dataclass
import heapq
import math
from itertools import count
from time import perf_counter
from .models import Market, State, Transfer
from .scheduling import Solution, objective, verify_solution, make_solution
from .validation import validate_state


@dataclass(frozen=True)
class OptimizationResult:
    status: str  # legacy search termination: optimal, infeasible, limit_reached
    best_solution: Solution | None
    expanded_states: int
    discovered_states: int
    proof_scope: str = 'empty initial offers: sequential just-in-time OFFER/BUY normal form for policy (1,0); historical fixed-message model otherwise'
    conclusion: str = 'unknown'  # optimal, feasible, infeasible, unknown
    lower_bound: tuple[int, int, int] | None = None
    optimality_gap: dict | None = None
    termination_reason: str = ''


def state_key(state: State) -> tuple:
    return state.owners, state.progress, state.balances


def objective_gap(incumbent: tuple[int, int, int] | None,
                  lower_bound: tuple[int, int, int] | None) -> dict | None:
    """Gap only at the first unresolved lexicographic coordinate, not a norm."""
    if incumbent is None or lower_bound is None:
        return None
    for index, (upper, lower) in enumerate(zip(incumbent, lower_bound)):
        if upper != lower:
            return {'coordinate': ('messages', 'transactions', 'gross_payments')[index],
                    'absolute': upper - lower, 'relative': (upper-lower)/upper if upper else None,
                    'earlier_coordinates_equal': True}
    return {'coordinate': None, 'absolute': 0, 'relative': 0.0, 'earlier_coordinates_equal': True}


def reference_quality(reference: Solution, optimum: Solution | None) -> dict:
    return {'reference_objective': reference.objective,
            'proven_optimum': optimum.objective if optimum else None,
            'reference_is_optimal': reference.objective == optimum.objective if optimum else None,
            'lexicographic_excess': objective_gap(reference.objective, optimum.objective) if optimum else None,
            'component_differences': tuple(a-b for a,b in zip(reference.objective, optimum.objective)) if optimum else None}


def solve_exact(market: Market, initial: State, state_limit: int = 20000,
                incumbent: Solution | None = None, *, use_lower_bound: bool = True,
                time_limit_seconds: float | None = None) -> OptimizationResult:
    """Fixed-policy exact search. Limits never establish infeasibility.

    Each unmet (agent,token) requires a distinct transfer. K unmet requirements
    therefore lower-bound remaining transfers; fixed per-trade messages give qK.
    Each unmet buyer must pay at least its minimum incoming price, so summing these
    gives a gross-payment lower bound. These coordinatewise bounds are admissible
    and consistent, including q=0. Search stores bitmask progress and path links,
    not copied histories/events; every returned witness is replayed independently.
    """
    validate_state(market, initial)
    if type(state_limit) is not int or state_limit < 0:
        raise ValueError('state_limit must be a nonnegative integer')
    if time_limit_seconds is not None and (not math.isfinite(time_limit_seconds) or time_limit_seconds < 0):
        raise ValueError('invalid time limit')
    if incumbent is not None:
        verify_solution(market, initial, incumbent)
    start_time = perf_counter()
    n = market.n_agents
    tasks = tuple(sum(1 << t for t in task) for task in market.tasks)
    initial_progress = tuple(sum(1 << t for t in p) for p in initial.progress)
    start = initial.owners, initial_progress, initial.balances
    q = market.communication.buyer + market.communication.seller
    min_price = tuple(min((market.prices[i][j] for j in range(n) if j != i), default=0) for i in range(n))

    def bound(key: tuple) -> tuple[int, int, int]:
        if not use_lower_bound:
            return (0, 0, 0)
        missing = tuple((task & ~seen).bit_count() for task, seen in zip(tasks, key[1]))
        k = sum(missing)
        return q * k, k, sum(c * price for c, price in zip(missing, min_price))

    def goal(key: tuple) -> bool:
        return all(task & ~seen == 0 for task, seen in zip(tasks, key[1]))

    def solution(link: tuple | None) -> Solution:
        actions = []
        while link is not None:
            action, link = link
            actions.append(action)
        result = Solution(tuple(reversed(actions)), (0, 0, 0))
        result = make_solution(market, result.actions)
        verify_solution(market, initial, result)
        return result

    serial = count()
    root_bound = bound(start)
    queue = [(root_bound, next(serial), (0, 0, 0), start, None)]
    best = {start: (0, 0, 0)}
    expanded = 0

    def finish(status: str, lower: tuple | None, reason: str) -> OptimizationResult:
        conclusion = status if status in ('optimal', 'infeasible') else ('feasible' if incumbent else 'unknown')
        if incumbent is not None and lower is not None:
            lower = min(lower, incumbent.objective)
        if status == 'optimal':
            lower = incumbent.objective
        return OptimizationResult(status, incumbent, expanded, len(best), conclusion=conclusion,
                                  lower_bound=lower,
                                  optimality_gap=objective_gap(incumbent.objective if incumbent else None, lower),
                                  termination_reason=reason)

    while queue:
        priority, _, cost, key, link = heapq.heappop(queue)
        if cost != best[key]:
            continue
        if goal(key):
            incumbent = solution(link)
            return finish('optimal', cost, 'goal')
        if expanded >= state_limit:
            return finish('limit_reached', priority, 'state_limit')
        if time_limit_seconds is not None and perf_counter() - start_time >= time_limit_seconds:
            return finish('limit_reached', priority, 'time_limit')
        if incumbent is not None and priority >= incumbent.objective:
            return finish('optimal', incumbent.objective, 'frontier_bound')
        expanded += 1
        owners, progress, balances = key
        for t, seller in enumerate(owners):
            for buyer in range(n):
                if buyer == seller:
                    continue
                price = market.prices[buyer][seller]
                mb, ms = market.communication.counts(t, seller, buyer)
                if balances[buyer] < price + mb or balances[seller] < ms:
                    continue
                new_owners, new_progress, new_balances = list(owners), list(progress), list(balances)
                new_owners[t] = buyer
                new_progress[buyer] |= tasks[buyer] & (1 << t)
                new_balances[buyer] -= price + mb
                new_balances[seller] += price - ms
                nxt = tuple(new_owners), tuple(new_progress), tuple(new_balances)
                candidate = cost[0] + mb + ms, cost[1] + 1, cost[2] + price
                h = bound(nxt)
                estimate = tuple(a+b for a,b in zip(candidate,h))
                if incumbent is not None and estimate >= incumbent.objective:
                    continue
                if nxt in best and candidate >= best[nxt]:
                    continue
                next_link = (Transfer(t, seller, buyer), link)
                if goal(nxt):
                    incumbent = solution(next_link)
                    continue
                if nxt not in best and len(best) >= state_limit:
                    # Unexpanded siblings are bounded by current priority (consistency).
                    return finish('limit_reached', priority, 'label_limit')
                best[nxt] = candidate
                heapq.heappush(queue, (estimate, next(serial), candidate, nxt, next_link))
    return finish('optimal' if incumbent else 'infeasible', None, 'exhausted')
