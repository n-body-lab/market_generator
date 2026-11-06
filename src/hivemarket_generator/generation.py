import numpy as np
from .allocation import allocate_tokens
from .config import MarketConfig
from .models import ExecutionMessages, Market
from .prices import generate_prices
from .tasks import generate_tasks
from .validation import validate_market


def generate_instance(config: MarketConfig) -> Market:
    rng = np.random.default_rng(config.seed)
    market = Market(generate_prices(config, rng),
                    generate_tasks(config.n_agents, config.n_tokens, config.task_dependency_range, rng),
                    allocate_tokens(config.n_agents, config.n_tokens, config.ownership_concentration, rng),
                    ExecutionMessages(config.buyer_messages, config.seller_messages))
    validate_market(market)
    return market
