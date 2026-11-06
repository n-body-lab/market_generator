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
    target_indirect_dependency_fraction: float | None = None
    structural_constraints: dict[str, tuple[float, float]] | None = None
    generation_attempt_limit: int = 100

    def __post_init__(self) -> None:
        for name in ('n_agents', 'n_tokens', 'max_candidate_depth', 'alternatives',
                     'price_modifications', 'buyer_messages', 'seller_messages',
                     'exact_state_limit', 'exact_max_agents', 'exact_max_tokens', 'seed', 'generation_attempt_limit'):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f'{name} must be a nonnegative integer')
        if self.n_agents < 1 or self.max_candidate_depth < 1 or self.alternatives < 1:
            raise ValueError('agents, depth and alternatives must be positive')
        if self.generation_attempt_limit < 1:
            raise ValueError('generation_attempt_limit must be positive')
        if self.target_indirect_dependency_fraction is not None and not (
                math.isfinite(self.target_indirect_dependency_fraction) and
                0 <= self.target_indirect_dependency_fraction <= 1):
            raise ValueError('invalid indirect fraction')
        from .constraints import PROPERTY_NAMES
        for name, interval in (self.structural_constraints or {}).items():
            if name not in PROPERTY_NAMES or len(interval) != 2:
                raise ValueError('unknown property or invalid interval')
            if any(not math.isfinite(v) or v < 0 for v in interval) or interval[0] > interval[1]:
                raise ValueError('invalid structural interval')
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
            'easy': dict(price_range=(1, 3), max_candidate_depth=1, budget_leeway=1.0,
                         structural_constraints={'indirect_dependency_fraction': (0, 0.15)}),
            'medium': dict(price_range=(1, 12), max_candidate_depth=2, budget_leeway=0.3,
                           structural_constraints={'indirect_dependency_fraction': (0.2, 0.5)}),
            'hard': dict(price_range=(1, 30), max_candidate_depth=3, budget_leeway=0.0,
                         ownership_concentration=0.15, price_modifications=3,
                         structural_constraints={'indirect_dependency_fraction': (0.6, 1.0)}),
        }
        if level not in params:
            raise ValueError('unknown difficulty preset')
        return cls(**(params[level] | overrides))
