"""Versioned JSON envelope; explicit typed decoder with invariant validation."""
from dataclasses import asdict, is_dataclass
import json
from typing import Any
from .models import Market, State, ExecutionMessages, Event, Transfer, initial_state, CommunicationEvent
from .validation import validate_market, validate_state


def primitive(value: Any) -> Any:
    if is_dataclass(value):
        return primitive(asdict(value))
    if isinstance(value, dict):
        return {(','.join(str(x) for x in k) if isinstance(k, tuple) else str(k)): primitive(v)
                for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return [primitive(v) for v in sorted(value)]
    if isinstance(value, (tuple, list)):
        return [primitive(v) for v in value]
    return value


def dumps(value: Any) -> str:
    return json.dumps({'schema_version': 'hivemarket/0.1', 'data': primitive(value)}, sort_keys=True,
                      indent=2, allow_nan=False)


def loads(text: str) -> Any:
    envelope = json.loads(text)
    if envelope['schema_version'] != 'hivemarket/0.1':
        raise ValueError('unsupported schema')
    return envelope['data']


def decode_market(data: dict[str, Any]) -> Market:
    market = Market(tuple(tuple(row) for row in data['prices']),
                    tuple(frozenset(task) for task in data['tasks']), tuple(data['initial_owners']),
                    ExecutionMessages(**data['communication']))
    validate_market(market)
    return market


def decode_state(market: Market, data: dict[str, Any]) -> State:
    events = tuple(Event(e['sequence'], Transfer(**e['transfer']), e['price'], e['buyer_messages'],
                         e['seller_messages'], e.get('signature')) for e in data['events'])
    state = State(tuple(data['owners']), tuple(data['balances']), tuple(frozenset(p) for p in data['progress']),
                  tuple(tuple(h) for h in data['histories']), events,
                  data['execution_messages'], data['exploratory_messages'])
    validate_state(market, state)
    return state


def decode_result(data: dict[str, Any]) -> 'GenerationResult':
    from .config import MarketConfig
    from .generation import GenerationResult
    from .scheduling import Solution, verify_solution
    from .validation import audit_solution
    market = decode_market(data['market'])
    initial = decode_state(market, data['initial_state'])
    config_data = dict(data['config'])
    for key in ('price_range', 'task_dependency_range'):
        config_data[key] = tuple(config_data[key])
    if isinstance(config_data['budget_leeway'], list):
        config_data['budget_leeway'] = tuple(config_data['budget_leeway'])
    if config_data.get('structural_constraints') is not None:
        config_data['structural_constraints'] = {k: tuple(v) for k,v in config_data['structural_constraints'].items()}
    def solution(raw: dict | None) -> Solution | None:
        if raw is None:
            return None
        value = Solution(tuple(Transfer(**a) for a in raw['actions']), tuple(raw['objective']))
        verify_solution(market, initial, value)
        audit_solution(market, initial, value)
        return value
    reference = solution(data['reference_solution'])
    if reference is None:
        raise ValueError('reference solution required')
    result = GenerationResult(
        market, initial, reference, tuple(data['reference_budgets']),
        tuple(tuple(r) for r in data['token_routes']),
        {tuple(int(x) for x in key.split(',')): tuple(tuple(p) for p in paths)
         for key, paths in data['candidates'].items()},
        MarketConfig(**config_data), data['seed'], data['feasibility_status'],
        data['optimality_status'], solution(data['optimal_solution']), solution(data['best_solution']),
        data['difficulty'], data['metadata'], data.get('status', 'optimal' if data['optimality_status'] == 'optimal' else 'feasible'))
    from .credits import reference_budgets, add_leeway
    from .routing import candidate_routes
    if (market.n_agents, market.n_tokens) != (result.config.n_agents, result.config.n_tokens):
        raise ValueError('inconsistent config dimensions')
    if result.seed != result.config.seed or result.feasibility_status != 'verified':
        raise ValueError('invalid generation status/seed')
    expected_budgets = reference_budgets(market, reference.actions)
    if result.reference_budgets != expected_budgets or initial.balances != add_leeway(
            expected_budgets, result.config.budget_leeway, result.config.leeway_mode):
        raise ValueError('inconsistent reference budgets')
    if initial != initial_state(
            market, initial.balances):
        raise ValueError('result must contain an initial state')
    expected_routes = [(o,) for o in market.initial_owners]
    for action in reference.actions:
        expected_routes[action.token] += (action.buyer,)
    if tuple(expected_routes) != result.token_routes:
        raise ValueError('inconsistent token routes')
    if result.candidates != candidate_routes(market.prices, result.config.max_candidate_depth,
                                            result.config.alternatives):
        raise ValueError('inconsistent candidates')
    if result.optimality_status not in ('optimal', 'not_run', 'limit_reached'):
        raise ValueError('invalid optimality status for feasible generation result')
    if result.optimality_status == 'optimal':
        from .optimization import solve_exact
        if result.optimal_solution is None:
            raise ValueError('optimal status requires solution')
        proof = solve_exact(market, initial, result.config.exact_state_limit, result.optimal_solution)
        if proof.status != 'optimal' or proof.best_solution.objective != result.optimal_solution.objective:
            raise ValueError('imported optimality claim could not be verified')
    elif result.optimal_solution is not None:
        raise ValueError('unproven optimal solution')
    from .constraints import requested_properties, realised_properties, satisfies
    if not satisfies(requested_properties(result.config), realised_properties(result)):
        raise ValueError('import violates structural constraints')
    if result.status != ('optimal' if result.optimal_solution else 'feasible'):
        raise ValueError('inconsistent conclusion')
    return result


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .generation import GenerationResult


def decode_ledger(data: list[dict[str, Any]]) -> tuple[Event | CommunicationEvent, ...]:
    """Decode an ordered continuation ledger; economic validation needs an anchor.

    Transfer records have a `transfer` object; exploratory records have exactly
    sender/recipient. This does not authenticate records or validate affordability.
    """
    records: list[Event | CommunicationEvent] = []
    for raw in data:
        if 'transfer' in raw:
            fields = dict(raw)
            fields['transfer'] = Transfer(**fields['transfer'])
            records.append(Event(**fields))
        else:
            records.append(CommunicationEvent(**raw))
    return tuple(records)
