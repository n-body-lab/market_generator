"""Componentwise minimum initial credits for one fixed schedule."""
import math
from .models import Market, Transfer


def reference_budgets(market: Market, actions: tuple[Transfer, ...]) -> tuple[int, ...]:
    spent = [0] * market.n_agents
    required = [0] * market.n_agents
    owners = list(market.initial_owners)
    for action in actions:
        t, s, b = action.token, action.seller, action.buyer
        if (not 0 <= t < market.n_tokens or not 0 <= b < market.n_agents
                or not 0 <= s < market.n_agents or s == b or owners[t] != s):
            raise ValueError('invalid schedule ownership')
        price = market.prices[b][s]
        mb, ms = market.communication.counts(t, s, b)
        required[b] = max(required[b], spent[b] + price + mb)
        required[s] = max(required[s], spent[s] + ms)
        spent[b] += price + mb
        spent[s] += ms - price
        owners[t] = b
    return tuple(required)


def add_leeway(budgets: tuple[int, ...], leeway: float | tuple[float, ...], mode: str) -> tuple[int, ...]:
    values = (float(leeway),) * len(budgets) if isinstance(leeway, (int, float)) else leeway
    if len(values) != len(budgets) or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('invalid leeway')
    if mode not in ('relative', 'absolute'):
        raise ValueError('invalid mode')
    return tuple(b + math.ceil(v * b if mode == 'relative' else v) for b, v in zip(budgets, values))
