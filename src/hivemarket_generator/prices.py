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
