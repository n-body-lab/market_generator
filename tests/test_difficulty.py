from hivemarket_generator import *
from hivemarket_generator.scheduling import verify_solution


def test_metrics_and_result_roundtrip():
    r = generate_market(MarketConfig())
    decoded = decode_result(loads(dumps(r)))
    assert decoded.market == r.market
    assert decoded.config == r.config
    assert dumps(decoded) == dumps(r)
    verify_solution(decoded.market, decoded.initial_state, decoded.reference_solution)
    metrics = r.difficulty
    assert sum(metrics['routing']['token_walk_lengths']) == r.reference_solution.objective[1]
    assert metrics['resources']['execution_communication_expenditure'] == r.reference_solution.objective[0]
    assert 0 <= metrics['resources']['fraction_limited_slack'] <= 1
    assert metrics['discovery_proxies']['location_assignment_search_space'] >= 1


def test_fragility_destructive_affordable_action():
    # Agent 1 can buy irrelevant token 1 from agent 2, losing its ability to buy token 0.
    m = Market(((0, 2, 2), (2, 0, 2), (2, 2, 0)),
               (frozenset(), frozenset({0}), frozenset()), (0, 2))
    f = analyse_fragility(m, initial_state(m, (0, 3, 0)))
    assert f['baseline_status'] == 'optimal'
    assert f['preserving_actions'] >= 1
    assert f['destructive_actions'] >= 1
    assert f['one_credit_expenditure_sensitivity'][0]['status'] == 'infeasible'


def test_all_presets_have_explicit_valid_parameters():
    for level in ('easy', 'medium', 'hard'):
        r = generate_market(MarketConfig.preset(level))
        assert r.difficulty
        assert r.feasibility_status == 'verified'


def test_claimed_optimum_reverified_on_import():
    import pytest
    r = generate_market(MarketConfig(n_agents=2, n_tokens=2, task_dependency_range=(1, 2)))
    assert r.optimality_status == 'optimal'
    assert dumps(decode_result(loads(dumps(r)))) == dumps(r)
    data = loads(dumps(r))
    data['reference_budgets'][0] += 1
    with pytest.raises(ValueError, match='budgets'):
        decode_result(data)
