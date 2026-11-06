from dataclasses import replace
from itertools import product
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import complete
from hivemarket_generator.optimization import solve_exact
from hivemarket_generator.scheduling import Solution, objective, reference_schedule, verify_solution
from hivemarket_generator.validation import audit_solution
from hivemarket_generator.simulation import execute


def test_hand_optimum_and_infeasibility():
    m = Market(((0, 2), (3, 0)), (frozenset(), frozenset({0})), (0,))
    r = solve_exact(m, initial_state(m, (0, 4)))
    assert r.status == 'optimal'
    assert r.best_solution.objective == (1, 1, 3)
    audit_solution(m, initial_state(m, (0, 4)), r.best_solution)
    assert solve_exact(m, initial_state(m)).status == 'infeasible'
    assert solve_exact(m, initial_state(m, (0, 4)), 0).status == 'limit_reached'


def test_independent_cost_optima_are_not_joint_lexicographic_optimum():
    m = Market(((0, 1, 9), (1, 0, 1), (8, 1, 0)),
               (frozenset(), frozenset(), frozenset({0, 1})), (0, 0))
    routes, reference = reference_schedule(m)
    assert routes == ((0, 1, 2), (0, 1, 2))
    s = initial_state(m, (30, 30, 30))
    r = solve_exact(m, s, incumbent=reference)
    assert r.status == 'optimal'
    assert reference.objective == (4, 4, 4)
    assert r.best_solution.objective == (2, 2, 16)
    verify_solution(m, s, r.best_solution)


def test_joint_credit_order_requires_sales():
    m = Market(((0, 2), (2, 0)), (frozenset({1}), frozenset({0})), (0, 1), ExecutionMessages(0, 0))
    s = initial_state(m, (0, 2))
    result = solve_exact(m, s)
    assert result.status == 'optimal'
    assert result.best_solution.actions == (Transfer(0, 0, 1), Transfer(1, 1, 0))
    reversed_solution = Solution(tuple(reversed(result.best_solution.actions)), (0, 2, 4))
    with pytest.raises(ValueError):
        audit_solution(m, s, reversed_solution)


def brute_force(market, initial, depth):
    """Independent bounded enumeration oracle: no solver key/dominance logic."""
    layer = [(initial, ())]
    winners = []
    for _ in range(depth + 1):
        nxt = []
        for state, actions in layer:
            if complete(market, state):
                winners.append(objective(market, actions))
                continue
            for t, seller in enumerate(state.owners):
                for buyer in range(market.n_agents):
                    if buyer == seller:
                        continue
                    a = Transfer(t, seller, buyer)
                    try:
                        nxt.append((execute(market, state, a), actions + (a,)))
                    except ValueError:
                        pass
        layer = nxt
    return min(winners) if winners else None


@pytest.mark.parametrize('seed', range(8))
def test_exact_matches_enumeration(seed):
    config = MarketConfig(n_agents=2, n_tokens=2, task_dependency_range=(1, 2), seed=seed)
    r = generate_market(config)
    assert r.optimality_status == 'optimal'
    assert r.optimal_solution.objective == brute_force(r.market, r.initial_state, 5)
    audit_solution(r.market, r.initial_state, r.optimal_solution)


def test_cap_preserves_verified_incumbent_without_proof():
    r = generate_market(MarketConfig(n_agents=3, n_tokens=2, task_dependency_range=(1, 2), exact_state_limit=1))
    assert r.feasibility_status == 'verified'
    assert r.optimality_status == 'limit_reached'
    assert r.optimal_solution is None
    assert r.best_solution is not None
    audit_solution(r.market, r.initial_state, r.best_solution)


def test_invalid_incumbent_and_objective_rejected():
    r = generate_market(MarketConfig())
    false = replace(r.reference_solution, objective=(0, 0, 0))
    with pytest.raises(ValueError):
        solve_exact(r.market, r.initial_state, incumbent=false)
    with pytest.raises(ValueError):
        audit_solution(r.market, r.initial_state, false)
