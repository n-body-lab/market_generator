"""Reproducible generation parameters; credit quantities are integral units."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MarketConfig:
    n_agents: int = 6
    n_tokens: int = 12
    max_candidate_depth: int = 3
    ownership_concentration: float = 0.5
    task_dependency_range: tuple[int, int] = (1, 4)
    price_range: tuple[int, int] = (1, 12)
    price_distribution: str = "uniform"
    asymmetric_prices: bool = True
    alternatives: int = 3
    price_modifications: int = 0
    budget_leeway: float | tuple[float, ...] = 0.2
    leeway_mode: str = "relative"
    buyer_messages: int = 1
    seller_messages: int = 0
    exact_state_limit: int = 20000
    exact_max_agents: int = 3
    exact_max_tokens: int = 3
    seed: int = 42

    def __post_init__(self) -> None:
        for name in ('n_agents', 'n_tokens', 'max_candidate_depth', 'alternatives',
                     'price_modifications', 'buyer_messages', 'seller_messages',
                     'exact_state_limit', 'exact_max_agents', 'exact_max_tokens', 'seed'):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f'{name} must be a nonnegative integer')
        if self.n_agents < 1 or self.max_candidate_depth < 1 or self.alternatives < 1:
            raise ValueError('agents, depth and alternatives must be positive')
        lo, hi = self.task_dependency_range
        if not (0 <= lo <= hi <= self.n_tokens) or any(type(x) is not int for x in (lo, hi)):
            raise ValueError('invalid task dependency range')
        lo, hi = self.price_range
        if not (1 <= lo <= hi) or any(type(x) is not int for x in (lo, hi)):
            raise ValueError('invalid integral price range')
        if not math.isfinite(self.ownership_concentration) or self.ownership_concentration <= 0:
            raise ValueError('concentration must be finite and positive')
        values = (self.budget_leeway,) if isinstance(self.budget_leeway, (int, float)) else self.budget_leeway
        if len(values) not in (1, self.n_agents) or any(not math.isfinite(x) or x < 0 for x in values):
            raise ValueError('invalid leeway')
        if self.leeway_mode not in ('absolute', 'relative'):
            raise ValueError('invalid leeway mode')
        if self.price_distribution not in ('uniform', 'triangular'):
            raise ValueError('invalid distribution')

    @classmethod
    def preset(cls, level: str, **overrides: object) -> 'MarketConfig':
        params = {
            'easy': dict(price_range=(1, 3), max_candidate_depth=1, budget_leeway=1.0),
            'medium': dict(price_range=(1, 12), max_candidate_depth=2, budget_leeway=0.3),
            'hard': dict(price_range=(1, 30), max_candidate_depth=3, budget_leeway=0.0,
                         ownership_concentration=0.15, price_modifications=3),
        }
        if level not in params:
            raise ValueError('unknown difficulty preset')
        return cls(**(params[level] | overrides))
