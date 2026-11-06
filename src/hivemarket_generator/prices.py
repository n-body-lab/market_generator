import numpy as np
from .config import MarketConfig


def generate_prices(config: MarketConfig, rng: np.random.Generator) -> tuple[tuple[int, ...], ...]:
    lo, hi = config.price_range
    n = config.n_agents
    if config.price_distribution == 'uniform':
        values = rng.integers(lo, hi + 1, size=(n, n))
    elif lo == hi:
        values = np.full((n, n), lo)
    else:
        values = np.rint(rng.triangular(lo, (lo + hi) / 2, hi, size=(n, n))).astype(int)
    if not config.asymmetric_prices:
        values = np.triu(values, 1) + np.triu(values, 1).T
    np.fill_diagonal(values, 0)
    return tuple(tuple(int(x) for x in row) for row in values)


def modify_prices(prices: tuple[tuple[int, ...], ...], count: int,
                  rng: np.random.Generator,
                  dependencies: tuple[tuple[int, int], ...] = ()) -> tuple[tuple[int, ...], ...]:
    """Raise selected direct prices above a two-edge alternative; retain all edges."""
    values = [list(row) for row in prices]
    n = len(values)
    if n < 3:
        return prices
    for _ in range(count):
        if dependencies:
            seller, buyer = dependencies[int(rng.integers(len(dependencies)))]
            middle = int(rng.choice([i for i in range(n) if i not in (seller, buyer)]))
        else:
            seller, middle, buyer = (int(x) for x in rng.choice(n, 3, replace=False))
        values[buyer][seller] = max(values[buyer][seller], values[middle][seller] + values[buyer][middle] + 1)
    return tuple(tuple(row) for row in values)
