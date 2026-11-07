from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.optimization import objective_gap, reference_quality


@pytest.mark.parametrize('seed', range(12))
def test_bound_matches_uniform_cost_and_is_valid_at_limit(seed):
    r = generate_market(MarketConfig(n_agents=3, n_tokens=2, task_dependency_range=(0, 2),
                                     buyer_messages=seed % 2, communication_protocol='legacy_fixed_messages', seed=seed, exact_state_limit=0))
    a = solve_exact(r.market, r.initial_state, 50000, r.reference_solution)
    b = solve_exact(r.market, r.initial_state, 50000, r.reference_solution, use_lower_bound=False)
    assert a.conclusion == b.conclusion == 'optimal'
    assert a.best_solution.objective == b.best_solution.objective
    assert a.lower_bound == a.best_solution.objective
    limited = solve_exact(r.market, r.initial_state, 1, r.reference_solution)
    assert limited.lower_bound <= a.best_solution.objective
    assert limited.best_solution.objective >= a.best_solution.objective


def test_limits_unified_status_and_lex_gap():
    r = economic_family('fragile')
    assert solve_exact(r.market, r.initial_state, 0).conclusion == 'unknown'
    limited = solve_exact(r.market, r.initial_state, 0, r.reference_solution)
    assert limited.conclusion == 'feasible'
    timed = solve_exact(r.market, r.initial_state, time_limit_seconds=0)
    assert timed.conclusion == 'unknown' and timed.termination_reason == 'time_limit'
    assert solve_exact(r.market, initial_state(r.market)).conclusion == 'infeasible'
    assert objective_gap((2, 2, 10), (1, 1, 100))['absolute'] == 1
    assert objective_gap((2, 2, 10), (2, 2, 8))['coordinate'] == 'gross_payments'
    assert generate_market(MarketConfig()).status == 'feasible'
