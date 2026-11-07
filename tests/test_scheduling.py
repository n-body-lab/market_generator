from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import complete
from hivemarket_generator.simulation import execute, replay, send_exploratory_message
from hivemarket_generator.credits import reference_budgets
from hivemarket_generator.routing import candidate_routes, independent_token_route
from hivemarket_generator.scheduling import verify_solution
from hivemarket_generator.validation import validate_state


def cycle_market(messages=ExecutionMessages()):
    return Market(((0, 2, 5), (2, 0, 2), (5, 2, 0)),
                  (frozenset(), frozenset({0}), frozenset({0})), (0,), messages)


def test_cycles_persistence_conservation_and_history():
    m = cycle_market()
    s = initial_state(m, (20, 20, 20))
    actions = (Transfer(0, 0, 1), Transfer(0, 1, 0), Transfer(0, 0, 2))
    final = replay(m, s, actions)
    assert complete(m, final)
    assert final.histories == ((0, 1, 0, 2),)
    assert sum(final.balances) == 60 - 3
    assert 0 in final.progress[1]
    validate_state(m, final)
    with pytest.raises(ValueError):
        validate_state(m, replace(final, histories=((0, 2),)))
    after_message = send_exploratory_message(m, final, 1, 2)
    assert sum(after_message.balances) == sum(final.balances) - 1
    assert after_message.exploratory_messages == 1
    no_messages = replace(m, communication=ExecutionMessages(0, 0), communication_protocol='legacy_fixed_messages')
    assert sum(replay(no_messages, s, actions).balances) == 60


def test_budget_minimum_including_sale_financing():
    m = cycle_market(ExecutionMessages(1, 1))
    actions = (Transfer(0, 0, 1), Transfer(0, 1, 2))
    required = reference_budgets(m, actions)
    assert required == (1, 4, 3)  # agent 1 must retain its seller message credit
    s = initial_state(m, required)
    replay(m, s, actions)
    for i, amount in enumerate(required):
        if amount:
            fewer = list(required)
            fewer[i] -= 1
            with pytest.raises(ValueError):
                replay(m, initial_state(m, tuple(fewer)), actions)


def test_bounded_paths_and_changed_prices():
    prices = ((0, 8, 8), (1, 0, 8), (8, 1, 0))
    before = candidate_routes(prices)
    assert before[0, 2][0] == (0, 1, 2)
    after = candidate_routes(((0, 8, 8), (1, 0, 8), (1, 1, 0)))
    assert after[0, 2][0] == (0, 2)
    assert all(len(p) <= 4 for paths in before.values() for p in paths)


def test_independent_route_can_revisit_hub():
    m = Market(((0, 1, 1), (1, 0, 20), (1, 20, 0)),
               (frozenset(), frozenset({0}), frozenset({0})), (0,))
    route = independent_token_route(m, 0)
    assert route in ((0, 1, 0, 2), (0, 2, 0, 1))


@pytest.mark.parametrize('seed', range(12))
def test_joint_generation(seed):
    result = generate_market(MarketConfig(seed=seed, price_modifications=3))
    final = verify_solution(result.market, result.initial_state, result.reference_solution)
    assert complete(result.market, final)
    assert result == generate_market(result.config)


def test_empty_market_tasks():
    r = generate_market(MarketConfig(n_agents=1, n_tokens=0, task_dependency_range=(0, 0)))
    assert r.reference_solution.actions == ()
    assert r.reference_budgets == (0,)


def test_sale_proceeds_finance_later_purchase():
    m = cycle_market(ExecutionMessages(0, 0))
    actions = (Transfer(0, 0, 1), Transfer(0, 1, 0))
    assert reference_budgets(m, actions) == (0, 2, 0)
    replay(m, initial_state(m, (0, 2, 0)), actions)


def test_price_modification_recomputes_selected_paths():
    import numpy as np
    from hivemarket_generator.prices import modify_prices
    prices = ((0, 1, 1), (1, 0, 1), (1, 1, 0))
    before = candidate_routes(prices)
    modified = modify_prices(prices, 1, np.random.default_rng(1))
    after = candidate_routes(modified)
    assert any(before[pair][0] != after[pair][0] for pair in before)
    assert all(p > 0 for i, row in enumerate(modified) for j, p in enumerate(row) if i != j)


def test_complete_journey_exceeds_candidate_depth():
    from hivemarket_generator.scheduling import reference_schedule, verify_solution
    from hivemarket_generator.credits import reference_budgets
    n = 5
    prices = tuple(tuple(0 if i == j else (1 if 0 in (i, j) else 30)
                         for j in range(n)) for i in range(n))
    m = Market(prices, (frozenset(),) + (frozenset({0}),) * 4, (0,))
    routes, solution = reference_schedule(m)
    assert len(routes[0]) - 1 == 7
    verify_solution(m, initial_state(m, reference_budgets(m, solution.actions)), solution)
