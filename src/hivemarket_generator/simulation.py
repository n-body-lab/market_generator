"""Atomic enforcement. All failed actions leave the immutable state unchanged."""
from dataclasses import replace
from .models import Market, State, Transfer, Event


def execute(market: Market, state: State, action: Transfer) -> State:
    t, s, b = action.token, action.seller, action.buyer
    if (not 0 <= t < market.n_tokens or not 0 <= s < market.n_agents
            or not 0 <= b < market.n_agents or s == b or state.owners[t] != s):
        raise ValueError('invalid transfer or seller does not own token')
    price = market.prices[b][s]
    mb, ms = market.communication.counts(t, s, b)
    if state.balances[b] < price + mb or state.balances[s] < ms:
        raise ValueError('unaffordable action')
    balances = list(state.balances)
    balances[b] -= price + mb
    balances[s] += price - ms
    owners = list(state.owners)
    owners[t] = b
    progress = list(state.progress)
    if t in market.tasks[b]:
        progress[b] = progress[b] | {t}
    histories = list(state.histories)
    histories[t] += (b,)
    event = Event(len(state.events), action, price, mb, ms)
    return State(tuple(owners), tuple(balances), tuple(progress), tuple(histories),
                 state.events + (event,), state.execution_messages + mb + ms, state.exploratory_messages)


def send_exploratory_message(market: Market, state: State, sender: int, recipient: int) -> State:
    if not (0 <= sender < market.n_agents and 0 <= recipient < market.n_agents) or sender == recipient:
        raise ValueError('invalid message endpoints')
    if state.balances[sender] < 1:
        raise ValueError('unaffordable message')
    balances = list(state.balances)
    balances[sender] -= 1
    return replace(state, balances=tuple(balances), exploratory_messages=state.exploratory_messages + 1)


def replay(market: Market, initial: State, actions: tuple[Transfer, ...]) -> State:
    state = initial
    for action in actions:
        state = execute(market, state, action)
    return state
