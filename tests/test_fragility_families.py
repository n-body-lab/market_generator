import pytest
from hivemarket_generator import *
from hivemarket_generator.models import complete
from hivemarket_generator.simulation import execute


@pytest.mark.parametrize('seed', range(5))
def test_hand_verified_family_fractions(seed):
    for name, expected in [('robust', 0), ('fragile', .5), ('highly_constrained', 5/6)]:
        r = economic_family(name, seed)
        f = analyse_fragility(r.market, r.initial_state, state_limit=10000)
        assert f['fragility_status'] == 'exact'
        assert f['decision_fragility'] == expected
        if name != 'robust':
            assert f['preserving_actions'] == 1
            for classified in f['actions']:
                after = execute(r.market, r.initial_state, classified['action'])
                # Independent deadlock argument: right purchase completes immediately;
                # wrong purchase leaves every balance below price+message.
                assert classified['preserves_feasibility'] == complete(r.market, after)
                if not complete(r.market, after):
                    assert max(after.balances) < r.market.prices[0][1] + 1
    robust = economic_family('robust', seed)
    counts = count_feasible_sequences(robust.market, robust.initial_state, 2)
    assert counts['count'] == 2


def test_unclassified_and_dead_states_have_no_fabricated_metric():
    r = economic_family('fragile')
    f = analyse_fragility(r.market, r.initial_state, state_limit=0)
    assert f['decision_fragility'] is None
    assert f['fragility_status'] == 'unavailable_search_limit'
    dead = initial_state(r.market)
    assert analyse_fragility(r.market, dead)['fragility_status'] == 'no_affordable_actions'
    assert count_feasible_sequences(r.market, r.initial_state, 3, 0)['count'] is None


def test_paired_leeway_preserves_structure_and_financing_count():
    from dataclasses import replace
    from hivemarket_generator.generation import prepare_market
    r = economic_family('fragile')
    loose = prepare_market(r.market, replace(r.config, budget_leeway=10))
    assert r.market == loose.market
    assert analyse_fragility(loose.market, loose.initial_state)['decision_fragility'] == 0
    swap = economic_family('robust')
    tight = prepare_market(swap.market, replace(swap.config, budget_leeway=0))
    assert financing_dependence(tight)['purchases_requiring_prior_sale_receipts'] == 1
