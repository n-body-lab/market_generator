from dataclasses import fields
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import LocalView
from hivemarket_generator.simulation import replay
from hivemarket_generator.constraints import realised_properties, satisfies, requested_properties


@pytest.mark.parametrize('level', ['easy', 'medium', 'hard'])
def test_pilot_interface_is_reproducible_complete_and_private(level):
    c = MarketConfig.preset(level, seed=42, exact_state_limit=1000)
    a, b = generate_market(c), generate_market(c)
    assert dumps(a) == dumps(b)
    assert a.metadata['constraints_satisfied']
    assert satisfies(requested_properties(c), realised_properties(a))
    raw = loads(dumps(a))
    assert {'config', 'initial_state', 'market', 'reference_solution', 'status',
            'optimality_status', 'difficulty', 'seed', 'metadata'} <= raw.keys()
    assert {'prices', 'tasks', 'initial_owners', 'communication'} == raw['market'].keys()
    assert {'owners', 'balances', 'progress', 'histories', 'events',
            'execution_messages', 'exploratory_messages'} == raw['initial_state'].keys()
    restored = decode_result(raw)
    final = replay(restored.market, restored.initial_state, restored.reference_solution.actions)
    validate_economic_state(restored.market, restored.initial_state, final, final.events)
    assert restored.status in ('optimal', 'feasible')
    assert (restored.optimal_solution is not None) == (restored.status == 'optimal')
    allowed = {'agent', 'n_agents', 'balance', 'inventory', 'task', 'progress', 'buying_prices', 'selling_prices'}
    assert {f.name for f in fields(LocalView)} == allowed
    for agent in range(c.n_agents):
        view = local_view(restored.market, restored.initial_state, agent)
        payload = loads(dumps(view))
        assert payload.keys() == allowed
        assert view.task == restored.market.tasks[agent]
        assert view.buying_prices == restored.market.prices[agent]
        assert view.selling_prices == tuple(row[agent] for row in restored.market.prices)
