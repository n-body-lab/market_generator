from dataclasses import dataclass
from .models import Market, State, Transfer, complete
from .routing import independent_token_route
from .simulation import replay
from .validation import validate_state, validate_economic_state
from .offers import (ProtocolAction, OfferState, reference_protocol, uses_offer_protocol,
                     replay_protocol, validate_offer_execution, protocol_summary)


@dataclass(frozen=True)
class Solution:
    actions: tuple[Transfer, ...]
    objective: tuple[int, int, int]
    protocol_actions: tuple[ProtocolAction, ...] | None = None


def objective(market: Market, actions: tuple[Transfer, ...]) -> tuple[int, int, int]:
    return (sum(sum(market.communication.counts(a.token, a.seller, a.buyer)) for a in actions),
            len(actions), sum(market.prices[a.buyer][a.seller] for a in actions))


def reference_schedule(market: Market) -> tuple[tuple[tuple[int, ...], ...], Solution]:
    routes = tuple(independent_token_route(market, t) for t in range(market.n_tokens))
    # Stable round-robin interleaving preserves every token's unique-owner order.
    actions = tuple(Transfer(t, route[step], route[step + 1])
                    for step in range(max((len(r) - 1 for r in routes), default=0))
                    for t, route in enumerate(routes) if step + 1 < len(route))
    return routes, make_solution(market, actions)


def make_solution(market: Market, actions: tuple[Transfer, ...]) -> Solution:
    return Solution(actions, objective(market, actions),
                    reference_protocol(actions) if uses_offer_protocol(market) else None)


def verify_protocol_solution(market: Market, initial: State, solution: Solution) -> OfferState:
    if not isinstance(initial, State):
        raise ValueError('solution verification requires a compact State with empty initial offers')
    validate_state(market, initial)
    if not uses_offer_protocol(market):
        raise ValueError('historical fee policy is not the revised protocol')
    plan = solution.protocol_actions if solution.protocol_actions is not None else reference_protocol(solution.actions)
    final = replay_protocol(market, initial, plan)
    validate_offer_execution(market, OfferState(initial), final, plan)
    transfers = tuple(e.transfer for e in final.economy.events[len(initial.events):])
    cost = protocol_summary(market, initial, final)
    actual = (cost['communication_expenditure'], cost['transactions'], cost['gross_trading_expenditure'])
    if transfers != solution.actions or actual != solution.objective or not complete(market, final.economy):
        raise ValueError('protocol projection, objective or task completion mismatch')
    return final


def verify_solution(market: Market, initial: State, solution: Solution) -> State:
    validate_state(market, initial)
    explicit = verify_protocol_solution(market, initial, solution) if uses_offer_protocol(market) else None
    final = replay(market, initial, solution.actions)
    validate_economic_state(market, initial, final, final.events[len(initial.events):])
    if not complete(market, final) or objective(market, solution.actions) != solution.objective:
        raise ValueError('incomplete solution or false objective')
    if explicit is not None and (explicit.economy.balances != final.balances
                                 or explicit.economy.histories != final.histories):
        raise ValueError('compact and explicit protocol executions disagree')
    if sum(initial.balances) - sum(final.balances) != final.execution_messages - initial.execution_messages:
        raise ValueError('credit accounting failure')
    return final
