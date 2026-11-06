from dataclasses import dataclass
from .models import Market, State, Transfer, complete
from .routing import independent_token_route
from .simulation import replay
from .validation import validate_state, validate_economic_state


@dataclass(frozen=True)
class Solution:
    actions: tuple[Transfer, ...]
    objective: tuple[int, int, int]


def objective(market: Market, actions: tuple[Transfer, ...]) -> tuple[int, int, int]:
    return (sum(sum(market.communication.counts(a.token, a.seller, a.buyer)) for a in actions),
            len(actions), sum(market.prices[a.buyer][a.seller] for a in actions))


def reference_schedule(market: Market) -> tuple[tuple[tuple[int, ...], ...], Solution]:
    routes = tuple(independent_token_route(market, t) for t in range(market.n_tokens))
    # Stable round-robin interleaving preserves every token's unique-owner order.
    actions = tuple(Transfer(t, route[step], route[step + 1])
                    for step in range(max((len(r) - 1 for r in routes), default=0))
                    for t, route in enumerate(routes) if step + 1 < len(route))
    return routes, Solution(actions, objective(market, actions))


def verify_solution(market: Market, initial: State, solution: Solution) -> State:
    validate_state(market, initial)
    final = replay(market, initial, solution.actions)
    validate_economic_state(market, initial, final, final.events[len(initial.events):])
    if not complete(market, final) or objective(market, solution.actions) != solution.objective:
        raise ValueError('incomplete solution or false objective')
    if sum(initial.balances) - sum(final.balances) != final.execution_messages - initial.execution_messages:
        raise ValueError('credit accounting failure')
    return final
