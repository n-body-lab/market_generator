from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.validation import validate_market, validate_state


def test_seed_and_roundtrip():
    m = generate_instance(MarketConfig())
    assert m == generate_instance(MarketConfig())
    assert m != generate_instance(MarketConfig(seed=43))
    assert decode_market(loads(dumps(m))) == m
    s = initial_state(m)
    assert decode_state(m, loads(dumps(s))) == s
    validate_state(m, s)


def test_ownership_and_local_boundary():
    m = generate_instance(MarketConfig(n_tokens=100, ownership_concentration=0.01))
    assert len(m.initial_owners) == 100
    assert max(m.initial_owners.count(i) for i in range(m.n_agents)) > 50
    view = local_view(m, initial_state(m), 0)
    assert not hasattr(view, 'initial_owners') and not hasattr(view, 'tasks')
    assert view.selling_prices == tuple(row[0] for row in m.prices)


@pytest.mark.parametrize('prices', [((0, 0), (1, 0)), ((0, float('inf')), (1, 0)), ((1, 2), (3, 0))])
def test_invalid_prices(prices):
    with pytest.raises(ValueError):
        validate_market(Market(prices, (frozenset(), frozenset()), (0,)))


def test_price_generation():
    m = generate_instance(MarketConfig())
    assert any(m.prices[i][j] != m.prices[j][i] for i in range(6) for j in range(6))
    symmetric = generate_instance(MarketConfig(asymmetric_prices=False, price_distribution='triangular'))
    assert all(symmetric.prices[i][j] == symmetric.prices[j][i] for i in range(6) for j in range(6))


@pytest.mark.parametrize('kw', [dict(price_range=(0, 2)), dict(task_dependency_range=(4, 2)),
                                dict(budget_leeway=-1), dict(ownership_concentration=0)])
def test_bad_config(kw):
    with pytest.raises(ValueError):
        MarketConfig(**kw)
