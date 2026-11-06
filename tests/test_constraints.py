from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.constraints import realised_properties, satisfies, requested_properties


def test_success_recomputed_constraints_and_determinism():
    c = MarketConfig(target_indirect_dependency_fraction=0.5, price_modifications=4)
    a = generate_market(c)
    assert a == generate_market(c)
    actual = realised_properties(a)
    assert actual['indirect_dependency_fraction'] >= .5
    assert satisfies(requested_properties(c), actual)
    assert a.metadata['constraints_satisfied'] is True
    assert decode_result(loads(dumps(a))).market == a.market


def test_impossible_constraints_fail_with_attempt_evidence():
    c = MarketConfig(n_agents=2, n_tokens=2, task_dependency_range=(1, 2),
                     target_indirect_dependency_fraction=1, generation_attempt_limit=3)
    with pytest.raises(GenerationFailure) as error:
        generate_market(c)
    assert error.value.attempts == 3
    assert error.value.last_realised_properties['indirect_dependency_fraction'] == 0


def test_depth_and_overlap_targets():
    c = MarketConfig(structural_constraints={'depth_2_fraction': (.4, 1), 'shared_demand_fraction': (.5, 1)},
                     price_modifications=5)
    r = generate_market(c)
    assert realised_properties(r)['depth_2_fraction'] >= .4
    with pytest.raises(GenerationFailure):
        generate_market(replace(c, n_agents=2, n_tokens=4, generation_attempt_limit=2))


def test_requested_depth_is_not_silently_relaxed():
    c = MarketConfig(structural_constraints={'mean_dependency_depth': (1, 1)})
    r = generate_market(c)
    assert realised_properties(r)['mean_dependency_depth'] == 1
    for name in ('easy', 'medium', 'hard'):
        result = generate_market(MarketConfig.preset(name))
        assert satisfies(requested_properties(result.config), realised_properties(result))
