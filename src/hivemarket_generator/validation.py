from .models import Market, State


def validate_market(market: Market) -> None:
    n = market.n_agents
    if n < 1 or len(market.prices) != n or any(len(row) != n for row in market.prices):
        raise ValueError('invalid price matrix dimensions')
    for i, row in enumerate(market.prices):
        for j, price in enumerate(row):
            if type(price) is not int or (price != 0 if i == j else price <= 0):
                raise ValueError('prices require zero diagonal and positive integral off-diagonal')
    if any(type(o) is not int or not 0 <= o < n for o in market.initial_owners):
        raise ValueError('invalid owner')
    if any(type(t) is not int or not 0 <= t < market.n_tokens for task in market.tasks for t in task):
        raise ValueError('invalid task token')


def validate_state(market: Market, state: State) -> None:
    validate_market(market)
    if (len(state.owners) != market.n_tokens or len(state.histories) != market.n_tokens
            or len(state.balances) != market.n_agents or len(state.progress) != market.n_agents):
        raise ValueError('invalid state dimensions')
    if any(type(b) is not int or b < 0 for b in state.balances):
        raise ValueError('negative/noninteger balance')
    if any(type(o) is not int or not 0 <= o < market.n_agents for o in state.owners):
        raise ValueError('invalid current owner')
    if type(state.execution_messages) is not int or state.execution_messages < 0:
        raise ValueError('invalid execution messages')
    for t, history in enumerate(state.histories):
        if (not history or history[0] != market.initial_owners[t] or history[-1] != state.owners[t]
                or any(type(o) is not int or not 0 <= o < market.n_agents for o in history)):
            raise ValueError('invalid history')
    for i, task in enumerate(market.tasks):
        if state.progress[i] != frozenset(t for t in task if i in state.histories[t]):
            raise ValueError('progress inconsistent with provenance')
    histories = [(o,) for o in market.initial_owners]
    messages = 0
    for index, event in enumerate(state.events):
        action = event.transfer
        if not 0 <= action.token < market.n_tokens or not 0 <= action.buyer < market.n_agents:
            raise ValueError('invalid event IDs')
        if (type(event.sequence) is not int or event.sequence != index
                or histories[action.token][-1] != action.seller
                or action.buyer == action.seller or event.price != market.prices[action.buyer][action.seller]
                or (event.buyer_messages, event.seller_messages) != market.communication.counts(
                    action.token, action.seller, action.buyer)):
            raise ValueError('invalid transfer event')
        histories[action.token] += (action.buyer,)
        messages += event.buyer_messages + event.seller_messages
    if tuple(histories) != state.histories or messages != state.execution_messages:
        raise ValueError('history/events mismatch')
    if type(state.exploratory_messages) is not int or state.exploratory_messages < 0:
        raise ValueError('invalid exploratory messages')


def audit_solution(market: Market, initial: State, solution: 'Solution') -> None:
    """Independent arithmetic/ownership audit; does not call simulation.execute.

    Validates a continuation from any structurally valid state, including historic
    progress. Message balances are checked before incoming sale proceeds.
    """
    validate_state(market, initial)
    balances = list(initial.balances)
    owners = list(initial.owners)
    seen = [set(p) for p in initial.progress]
    gross = messages = 0
    for a in solution.actions:
        if (not 0 <= a.token < market.n_tokens or not 0 <= a.seller < market.n_agents
                or not 0 <= a.buyer < market.n_agents or a.buyer == a.seller or owners[a.token] != a.seller):
            raise ValueError('audit: invalid ownership')
        price = market.prices[a.buyer][a.seller]
        mb, ms = market.communication.counts(a.token, a.seller, a.buyer)
        if balances[a.buyer] < price + mb or balances[a.seller] < ms:
            raise ValueError('audit: insufficient credits')
        balances[a.buyer] -= price + mb
        balances[a.seller] += price - ms
        owners[a.token] = a.buyer
        if a.token in market.tasks[a.buyer]:
            seen[a.buyer].add(a.token)
        gross += price
        messages += mb + ms
    if any(not task <= progress for task, progress in zip(market.tasks, seen)):
        raise ValueError('audit: unsatisfied tasks')
    if solution.objective != (messages, len(solution.actions), gross):
        raise ValueError('audit: objective mismatch')
    if sum(balances) != sum(initial.balances) - messages:
        raise ValueError('audit: accounting failure')


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .scheduling import Solution
