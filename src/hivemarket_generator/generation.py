from dataclasses import dataclass, replace
import numpy as np
from .allocation import allocate_tokens
from .config import MarketConfig
from .models import ExecutionMessages, Market, State, initial_state
from .prices import generate_prices, modify_prices
from .tasks import generate_tasks
from .routing import candidate_routes
from .validation import validate_market, audit_solution, validate_market_config
from .offers import uses_offer_protocol
from .credits import reference_budgets, add_leeway, initial_endowments
from .scheduling import Solution, reference_schedule, verify_solution


def _candidate_instance(config: MarketConfig, rng: np.random.Generator) -> Market:
    prices = generate_prices(config, rng)
    owners = allocate_tokens(config.n_agents, config.n_tokens, config.ownership_concentration, rng)
    candidates = candidate_routes(prices, config.max_candidate_depth, config.alternatives)
    tasks = generate_tasks(config.n_agents, config.n_tokens, config.task_dependency_range, rng,
                           owners, candidates)
    dependencies = tuple((owners[t], i) for i, task in enumerate(tasks) for t in sorted(task) if owners[t] != i)
    final_prices = modify_prices(prices, config.price_modifications, rng, dependencies)
    market = Market(final_prices, tasks, owners, ExecutionMessages(config.buyer_messages, config.seller_messages),
                    communication_protocol=config.communication_protocol)
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
    status: str = 'feasible'


class GenerationFailure(RuntimeError):
    def __init__(self, attempts: int, requested: dict, realised: dict):
        self.attempts, self.requested_properties, self.last_realised_properties = attempts, requested, realised
        super().__init__(f'No candidate satisfied constraints after {attempts} attempts: {requested}; last={realised}')


def generate_instance(config: MarketConfig) -> Market:
    # Same constrained sampling semantics as generate_market; preserve public API.
    return generate_market(config).market


def generate_market(config: MarketConfig) -> GenerationResult:
    from .constraints import requested_properties, realised_properties, satisfies
    requested = requested_properties(config)
    rng = np.random.default_rng(config.seed)
    realised = {}
    for attempt in range(1, config.generation_attempt_limit + 1):
        market = _candidate_instance(config, rng)
        # Avoid spending exact-search work on candidates that will be rejected.
        candidate_config = replace(config, exact_state_limit=0, structural_constraints=None,
                                   target_indirect_dependency_fraction=None)
        result = prepare_market(market, candidate_config)
        realised = realised_properties(result)
        if satisfies(requested, realised):
            if config.exact_state_limit:
                result = prepare_market(market, config)
            else:
                result = replace(result, config=config)
            return replace(result, metadata=result.metadata | {
                'structure_source': 'seeded constrained generation', 'generation_attempts': attempt,
                'requested_properties': requested, 'realised_properties': realised,
                'constraints_satisfied': True})
    raise GenerationFailure(config.generation_attempt_limit, requested, realised)


def prepare_market(market: Market, config: MarketConfig) -> GenerationResult:
    """Benchmark a supplied market, using config for routing, budgets and search.

    No prices/tasks are regenerated. Metadata distinguishes supplied structures.
    """
    validate_market_config(market, config)
    # No stale paths survive price modification.
    candidates = candidate_routes(market.prices, config.max_candidate_depth, config.alternatives)
    routes, solution = reference_schedule(market)
    required = reference_budgets(market, solution.actions)
    before_floor = add_leeway(required, config.budget_leeway, config.leeway_mode)
    initial = initial_state(market, initial_endowments(required, config.budget_leeway, config.leeway_mode,
                                                     config.minimum_initial_credits))
    verify_solution(market, initial, solution)
    audit_solution(market, initial, solution)
    result = GenerationResult(market, initial, solution, required, routes, candidates, config, config.seed,
                            best_solution=solution,
                            metadata={'routing_objective': 'independent gross cost; exact per token up to 8 demanders',
                                      'execution_policy': ('one taxed OFFER per transaction; BUY untaxed; no discovery-cost claim'
                                                           if uses_offer_protocol(market) else
                                                           'historical fixed-message policy; not revised game rules'),
                                      'communication_protocol': market.communication_protocol,
                                      'seller_consent': 'assumed free cooperative SELL at each reference BUY',
                                      'package_version': '0.1.0',
                                      'credit_allocation': {
                                          'reference_budgets': required,
                                          'initial_credits_before_floor': before_floor,
                                          'initial_credits': initial.balances,
                                          'minimum_initial_credits': config.minimum_initial_credits,
                                          'zero_credit_agents': initial.balances.count(0),
                                          'agents_increased_by_floor': sum(b > old for b, old in zip(initial.balances, before_floor)),
                                          'additional_credits_from_floor': sum(initial.balances) - sum(before_floor),
                                          'zero_credit_agents_with_unfinished_tasks': sum(
                                              b == 0 and bool(task - seen) for b, task, seen in
                                              zip(initial.balances, market.tasks, initial.progress)),
                                          'zero_credit_agents_before_floor_with_unfinished_tasks': sum(
                                              b == 0 and bool(task - seen) for b, task, seen in
                                              zip(before_floor, market.tasks, initial.progress)),
                                      },
                                      'structure_source': 'supplied to prepare_market (generate_market uses seeded generation)'})

    if (market.n_agents <= config.exact_max_agents and market.n_tokens <= config.exact_max_tokens
            and config.exact_state_limit > 0):
        from .optimization import solve_exact
        exact = solve_exact(market, initial, config.exact_state_limit, solution)
        result = replace(result, status=exact.conclusion, optimality_status=exact.status,
                         optimal_solution=exact.best_solution if exact.status == 'optimal' else None,
                         best_solution=exact.best_solution,
                         metadata=result.metadata | {'exact_search': {
                             'expanded_states': exact.expanded_states, 'discovered_states': exact.discovered_states,
                             'proof_scope': exact.proof_scope, 'lower_bound': exact.lower_bound,
                             'optimality_gap': exact.optimality_gap, 'termination_reason': exact.termination_reason,
                             'incumbent_objective': exact.best_solution.objective if exact.best_solution else None}})
        if exact.best_solution is not None:
            audit_solution(market, initial, exact.best_solution)
    if uses_offer_protocol(market):
        from .scheduling import verify_protocol_solution
        from .offers import protocol_summary
        final = verify_protocol_solution(market, initial, solution)
        result = replace(result, metadata=result.metadata | {'reference_accounting': protocol_summary(market, initial, final)})
    from .optimization import reference_quality
    result = replace(result, metadata=result.metadata | {
        'reference_quality': reference_quality(solution, result.optimal_solution)})
    from .difficulty import analyse_difficulty
    result = replace(result, difficulty=analyse_difficulty(result))
    from .constraints import requested_properties, realised_properties, satisfies
    requested, realised = requested_properties(config), realised_properties(result)
    if not satisfies(requested, realised):
        raise GenerationFailure(1, requested, realised)
    return replace(result, metadata=result.metadata | {
        'requested_properties': requested, 'realised_properties': realised, 'constraints_satisfied': True})
