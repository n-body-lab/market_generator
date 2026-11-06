"""Finite, exact lexicographic state-space search with explicit proof status."""
from dataclasses import dataclass
import heapq
from itertools import count
from .models import Market, State, Transfer, complete
from .scheduling import Solution, objective, verify_solution
from .simulation import execute
from .validation import validate_state


@dataclass(frozen=True)
class OptimizationResult:
    status: str  # optimal, infeasible, limit_reached
    best_solution: Solution | None
    expanded_states: int
    discovered_states: int
    proof_scope: str = 'all feasible transfers with fixed budgets and V0.1 execution messages'


def state_key(state: State) -> tuple:
    return state.owners, state.progress, state.balances


def solve_exact(market: Market, initial: State, state_limit: int = 20000,
                incumbent: Solution | None = None) -> OptimizationResult:
    validate_state(market, initial)
    if type(state_limit) is not int or state_limit < 0:
        raise ValueError('state_limit must be a nonnegative integer')
    if incumbent is not None:
        verify_solution(market, initial, incumbent)
    serial = count()
    zero = (0, 0, 0)
    # Paths stored for small-instance clarity; cap bounds both expansion and labels.
    queue = [(zero, next(serial), initial, ())]
    best = {state_key(initial): zero}
    expanded = 0
    while queue:
        cost, _, state, actions = heapq.heappop(queue)
        if cost != best[state_key(state)]:
            continue
        if complete(market, state):
            solution = Solution(actions, cost)
            verify_solution(market, initial, solution)
            return OptimizationResult('optimal', solution, expanded, len(best))
        if incumbent is not None and cost >= incumbent.objective:
            return OptimizationResult('optimal', incumbent, expanded, len(best))
        if expanded >= state_limit:
            return OptimizationResult('limit_reached', incumbent, expanded, len(best))
        expanded += 1
        for t, seller in enumerate(state.owners):
            for buyer in range(market.n_agents):
                if buyer == seller:
                    continue
                action = Transfer(t, seller, buyer)
                try:
                    nxt = execute(market, state, action)
                except ValueError:
                    continue
                edge = objective(market, (action,))
                candidate = tuple(a + b for a, b in zip(cost, edge))
                if incumbent is not None and candidate >= incumbent.objective:
                    continue
                key = state_key(nxt)
                if key in best and candidate >= best[key]:
                    continue
                path = actions + (action,)
                if complete(market, nxt):
                    incumbent = Solution(path, candidate)
                    verify_solution(market, initial, incumbent)
                    continue
                if key not in best and len(best) >= state_limit:
                    return OptimizationResult('limit_reached', incumbent, expanded, len(best))
                best[key] = candidate
                heapq.heappush(queue, (candidate, next(serial), nxt, path))
    return OptimizationResult('optimal' if incumbent is not None else 'infeasible',
                              incumbent, expanded, len(best))
