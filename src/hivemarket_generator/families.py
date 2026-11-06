"""Controlled economic families, not agent policies. Seed varies the price scale."""
import numpy as np
from .config import MarketConfig
from .models import Market
from .generation import GenerationResult, prepare_market


def economic_family(name: str, seed: int = 42, decoys: int = 5,
                    budget_leeway: float = 0) -> GenerationResult:
    price = int(np.random.default_rng(seed).integers(2, 6))
    if name == 'robust':
        market = Market(((0, price), (price, 0)),
                        (frozenset({1}), frozenset({0})), (0, 1))
        config = MarketConfig(n_agents=2, n_tokens=2, task_dependency_range=(1, 1), seed=seed,
                              budget_leeway=price + 1 + budget_leeway, leeway_mode='absolute')
    elif name in ('fragile', 'highly_constrained'):
        count = 1 if name == 'fragile' else decoys
        if type(count) is not int or count < 1:
            raise ValueError('decoys must be positive')
        market = Market(tuple(tuple(0 if i == j else price for j in range(3)) for i in range(3)),
                        (frozenset(), frozenset({0}), frozenset()), (0,) + (2,) * count)
        config = MarketConfig(n_agents=3, n_tokens=count + 1, task_dependency_range=(0, 1), seed=seed,
                              budget_leeway=budget_leeway, leeway_mode='absolute')
    else:
        raise ValueError('unknown economic family')
    return prepare_market(market, config)
