from dataclasses import dataclass, replace
import numpy as np
from .allocation import allocate_tokens
from .config import MarketConfig
from .models import ExecutionMessages, Market, State, initial_state
from .prices import generate_prices, modify_prices
from .tasks import generate_tasks
from .routing import candidate_routes
from .validation import validate_market, audit_solution
from .credits import reference_budgets, add_leeway
from .scheduling import Solution, reference_schedule, verify_solution


def generate_instance(config: MarketConfig) -> Market:
    rng = np.random.default_rng(config.seed)
    prices = generate_prices(config, rng)
    owners = allocate_tokens(config.n_agents, config.n_tokens, config.ownership_concentration, rng)
    candidates = candidate_routes(prices, config.max_candidate_depth, config.alternatives)
    tasks = generate_tasks(config.n_agents, config.n_tokens, config.task_dependency_range, rng,
                           owners, candidates)
    final_prices = modify_prices(prices, config.price_modifications, rng)
    market = Market(final_prices, tasks, owners, ExecutionMessages(config.buyer_messages, config.seller_messages))
    validate_market(market)
    return market


@dataclass(frozen=True)
class GenerationResult:
    market: Market
    initial_state: State
    reference_solution: Solution
    reference_budgets: tuple[int, ...]
    token_routes: tuple[tuple[int, ...], ...]
    candidates: dict[tuple[int, int], tuple[tuple[int, ...], ...]]
    config: MarketConfig
    seed: int
    feasibility_status: str = 'verified'
    optimality_status: str = 'not_run'
    optimal_solution: Solution | None = None
    best_solution: Solution | None = None
    difficulty: dict | None = None
    metadata: dict | None = None


def generate_market(config: MarketConfig) -> GenerationResult:
    market = generate_instance(config)
    # No stale paths survive price modification.
    candidates = candidate_routes(market.prices, config.max_candidate_depth, config.alternatives)
    routes, solution = reference_schedule(market)
    required = reference_budgets(market, solution.actions)
    initial = initial_state(market, add_leeway(required, config.budget_leeway, config.leeway_mode))
    verify_solution(market, initial, solution)
    audit_solution(market, initial, solution)
    result = GenerationResult(market, initial, solution, required, routes, candidates, config, config.seed,
                            best_solution=solution,
                            metadata={'routing_objective': 'independent gross cost; exact per token up to 8 demanders',
                                      'execution_policy': 'fixed buyer/seller messages; no discovery-cost claim'})

    if (market.n_agents <= config.exact_max_agents and market.n_tokens <= config.exact_max_tokens
            and config.exact_state_limit > 0):
        from .optimization import solve_exact
        exact = solve_exact(market, initial, config.exact_state_limit, solution)
        result = replace(result, optimality_status=exact.status,
                         optimal_solution=exact.best_solution if exact.status == 'optimal' else None,
                         best_solution=exact.best_solution,
                         metadata=result.metadata | {'exact_search': {
                             'expanded_states': exact.expanded_states, 'discovered_states': exact.discovered_states,
                             'proof_scope': exact.proof_scope}})
        if exact.best_solution is not None:
            audit_solution(market, initial, exact.best_solution)
    return result
